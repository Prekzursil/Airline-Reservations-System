#!/usr/bin/env python3
from __future__ import absolute_import, annotations, division

import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable, TextIO, Tuple

_BRANCH_PREFIXES = ("BRDA:", "BRF:", "BRH:")
_IGNORED_PARTS = {".git", "build", "coverage", "coverage-100", "dist", "node_modules", "obj"}
_SOURCE_SUFFIXES = (".cpp", ".cc", ".c", ".h", ".hpp", ".py", ".js", ".jsx", ".ts", ".tsx")


@dataclass(frozen=True)
class _RepoFileIndexes:
    root: Path
    exact_paths: set[str]
    casefold_paths: dict[str, str]
    by_name: dict[str, list[str]]


@dataclass
class _RecordState:
    total: int = 0
    covered: int = 0
    saw_lf: bool = False
    saw_lh: bool = False
    active: bool = False


def _build_repo_file_indexes(repo_root: Path) -> _RepoFileIndexes:
    exact_paths: set[str] = set()
    casefold_paths: dict[str, str] = {}
    by_name: dict[str, list[str]] = defaultdict(list)
    for path in repo_root.rglob("*"):
        try:
            is_file = path.is_file()
        except OSError:
            continue
        if not is_file or _contains_ignored_parts(path.parts):
            continue
        relative_path = path.relative_to(repo_root).as_posix()
        exact_paths.add(relative_path)
        casefold_paths.setdefault(relative_path.casefold(), relative_path)
        by_name[path.name].append(relative_path)
    return _RepoFileIndexes(
        root=repo_root,
        exact_paths=exact_paths,
        casefold_paths=casefold_paths,
        by_name=dict(by_name),
    )


def _sanitize_relative_candidate(candidate: str) -> str:
    parts = [part for part in PurePosixPath(candidate).parts if part not in ("", ".")]
    if not parts or any(part == ".." for part in parts):
        return PurePosixPath(candidate).name
    return "/".join(parts)


def _contains_ignored_parts(parts: tuple[str, ...]) -> bool:
    return bool(_IGNORED_PARTS.intersection(parts))


def _trim_to_source_suffix(candidate: str) -> str:
    lowered = candidate.lower()
    suffix_ends = [
        index + len(suffix)
        for suffix in _SOURCE_SUFFIXES
        for index in [lowered.rfind(suffix)]
        if index != -1
    ]
    if not suffix_ends:
        return candidate
    return candidate[: max(suffix_ends)]


def _matching_repo_suffix(
    candidate: str,
    repo_paths: set[str],
    repo_paths_casefold: dict[str, str],
) -> str:
    normalized = _sanitize_relative_candidate(_trim_to_source_suffix(candidate))
    direct_match = repo_paths_casefold.get(normalized.casefold())
    if direct_match is not None:
        return direct_match
    parts = PurePosixPath(normalized).parts
    for index in range(len(parts)):
        suffix = "/".join(parts[index:])
        suffix_match = repo_paths_casefold.get(suffix.casefold())
        if suffix_match is not None:
            return suffix_match
    return normalized


def _normalize_absolute_candidate(candidate: str, repo_root_text: str) -> str:
    if not (candidate.startswith("/") or (len(candidate) >= 3 and candidate[1:3] == ":/")):
        return candidate
    prefix = f"{repo_root_text}/"
    if candidate == repo_root_text:
        return ""
    if candidate.startswith(prefix):
        return candidate[len(prefix) :]
    return PurePosixPath(candidate).as_posix()


def _normalize_source_path(
    raw_path: str,
    *,
    repo_indexes: _RepoFileIndexes,
) -> str:
    candidate = str(raw_path or "").strip().replace("\\", "/")
    while candidate.startswith("./"):
        candidate = candidate[2:]
    if not candidate:
        return candidate

    repo_root_text = repo_indexes.root.resolve(strict=False).as_posix().rstrip("/")
    candidate = _normalize_absolute_candidate(candidate, repo_root_text)

    candidate = _matching_repo_suffix(candidate, repo_indexes.exact_paths, repo_indexes.casefold_paths)
    if candidate in repo_indexes.exact_paths:
        return candidate

    basename = PurePosixPath(_trim_to_source_suffix(candidate)).name
    basename_matches = repo_indexes.by_name.get(basename, [])
    if len(basename_matches) == 1:
        return basename_matches[0]

    return candidate


def _flush_record(kept_lines: list[str], record: _RecordState) -> None:
    if not record.active:
        return
    if not record.saw_lf and record.total:
        kept_lines.append(f"LF:{record.total}")
    if not record.saw_lh and record.total:
        kept_lines.append(f"LH:{record.covered}")
    record.total = 0
    record.covered = 0
    record.saw_lf = False
    record.saw_lh = False
    record.active = False


def _handle_source_line(
    raw_line: str,
    *,
    kept_lines: list[str],
    record: _RecordState,
    repo_indexes: _RepoFileIndexes,
) -> None:
    _flush_record(kept_lines, record)
    normalized_source = _normalize_source_path(raw_line.split(":", 1)[1], repo_indexes=repo_indexes)
    kept_lines.append(f"SF:{normalized_source}")
    record.active = True


def _handle_da_line(
    raw_line: str,
    *,
    kept_lines: list[str],
    record: _RecordState,
    repo_indexes: _RepoFileIndexes | None = None,
) -> None:
    _ = repo_indexes
    kept_lines.append(raw_line)
    if not record.active:
        return
    _, hits, *_ = raw_line[3:].split(",")
    record.total += 1
    record.covered += int(float(hits) > 0)


def _handle_totals_line(
    raw_line: str,
    *,
    kept_lines: list[str],
    record: _RecordState,
    repo_indexes: _RepoFileIndexes | None = None,
) -> None:
    _ = repo_indexes
    kept_lines.append(raw_line)
    record.active = True
    is_lf = raw_line.startswith("LF:")
    record.saw_lf = record.saw_lf or is_lf
    record.saw_lh = record.saw_lh or not is_lf


def _classify_lcov_line(raw_line: str) -> str:
    if raw_line.startswith(_BRANCH_PREFIXES):
        return "branch"
    if raw_line == "end_of_record":
        return "end"
    return raw_line[:3]


_LCOV_LINE_HANDLERS = {
    "SF:": _handle_source_line,
    "DA:": _handle_da_line,
    "LF:": _handle_totals_line,
    "LH:": _handle_totals_line,
}


def normalize_lcov_lines(lines: Iterable[str], *, repo_root: Path | None = None) -> Tuple[str, int]:
    kept_lines = []
    stripped_count = 0
    repo_indexes = _build_repo_file_indexes((repo_root or Path.cwd()).resolve())
    record = _RecordState()

    for raw_line in lines:
        line_kind = _classify_lcov_line(raw_line)
        if line_kind == "branch":
            stripped_count += 1
            continue
        if line_kind == "end":
            _flush_record(kept_lines, record)
            kept_lines.append(raw_line)
            continue
        handler = _LCOV_LINE_HANDLERS.get(line_kind)
        if handler is None:
            kept_lines.append(raw_line)
            continue
        handler(raw_line, kept_lines=kept_lines, record=record, repo_indexes=repo_indexes)

    _flush_record(kept_lines, record)
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
