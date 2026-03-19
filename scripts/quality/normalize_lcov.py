#!/usr/bin/env python3
from __future__ import absolute_import, annotations, division

import sys
from collections import defaultdict
from pathlib import Path, PurePosixPath
from typing import Iterable, TextIO, Tuple

_BRANCH_PREFIXES = ("BRDA:", "BRF:", "BRH:")
_IGNORED_PARTS = {".git", "build", "coverage", "coverage-100", "dist", "node_modules", "obj"}


def _build_repo_file_indexes(repo_root: Path) -> tuple[set[str], dict[str, list[str]]]:
    exact_paths: set[str] = set()
    by_name: dict[str, list[str]] = defaultdict(list)
    for path in repo_root.rglob("*"):
        if not path.is_file() or any(part in _IGNORED_PARTS for part in path.parts):
            continue
        relative_path = path.relative_to(repo_root).as_posix()
        exact_paths.add(relative_path)
        by_name[path.name].append(relative_path)
    return exact_paths, dict(by_name)


def _sanitize_relative_candidate(candidate: str) -> str:
    parts = [part for part in PurePosixPath(candidate).parts if part not in ("", ".")]
    if not parts or any(part == ".." for part in parts):
        return PurePosixPath(candidate).name
    return "/".join(parts)


def _normalize_source_path(
    raw_path: str,
    *,
    repo_root: Path,
    repo_paths: set[str],
    repo_file_index: dict[str, list[str]],
) -> str:
    candidate = str(raw_path or "").strip().replace("\\", "/")
    while candidate.startswith("./"):
        candidate = candidate[2:]
    if not candidate:
        return candidate

    repo_root_text = repo_root.resolve(strict=False).as_posix().rstrip("/")
    if candidate.startswith("/") or (len(candidate) >= 3 and candidate[1:3] == ":/"):
        try:
            prefix = f"{repo_root_text}/"
            if candidate == repo_root_text:
                candidate = ""
            elif candidate.startswith(prefix):
                candidate = candidate[len(prefix) :]
            else:
                candidate = PurePosixPath(candidate).name
        except ValueError:
            candidate = PurePosixPath(candidate).name

    candidate = _sanitize_relative_candidate(candidate)
    if candidate in repo_paths:
        return candidate

    basename_matches = repo_file_index.get(PurePosixPath(candidate).name, [])
    if len(basename_matches) == 1:
        return basename_matches[0]

    return candidate


def normalize_lcov_lines(lines: Iterable[str], *, repo_root: Path | None = None) -> Tuple[str, int]:
    kept_lines = []
    stripped_count = 0
    root = (repo_root or Path.cwd()).resolve()
    repo_paths, repo_file_index = _build_repo_file_indexes(root)

    for raw_line in lines:
        if raw_line.startswith(_BRANCH_PREFIXES):
            stripped_count += 1
            continue
        if raw_line.startswith("SF:"):
            normalized_source = _normalize_source_path(
                raw_line.split(":", 1)[1],
                repo_root=root,
                repo_paths=repo_paths,
                repo_file_index=repo_file_index,
            )
            kept_lines.append(f"SF:{normalized_source}")
            continue
        kept_lines.append(raw_line)

    normalized = "\n".join(kept_lines)
    if normalized and not normalized.endswith("\n"):
        normalized += "\n"
    return normalized, stripped_count


def main(
    *,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    input_stream = stdin or sys.stdin
    output_stream = stdout or sys.stdout
    error_stream = stderr or sys.stderr

    normalized, stripped_count = normalize_lcov_lines(input_stream.read().splitlines())
    output_stream.write(normalized)
    error_stream.write(f"Normalized LCOV: stripped {stripped_count} branch records\n")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    raise SystemExit(main())
