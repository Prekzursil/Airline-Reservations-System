#!/usr/bin/env python3
"""Strip branch records from LCOV input while preserving line coverage."""

from __future__ import absolute_import, annotations, division

import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Dict, Iterable, List, TextIO, Tuple

_BRANCH_PREFIXES = ("BRDA:", "BRF:", "BRH:")
_SOURCE_SUFFIXES = (
    ".cpp",
    ".h",
    ".hpp",
    ".c",
    ".cc",
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
)


@dataclass(frozen=True)
class _RepoFileIndexes:
    """Repository-relative lookup indexes used for LCOV path normalization."""

    repo_root: Path
    by_name: Dict[str, List[str]]
    casefold_paths: Dict[str, str]


@dataclass
class _RecordState:
    """Mutable per-record LCOV counters tracked during normalization."""

    active: bool = False
    total: int = 0
    covered: int = 0
    saw_lf: bool = False
    saw_lh: bool = False


def _trim_to_source_suffix(raw_path: str) -> str:
    """Trim known LCOV suffix noise after a source filename."""
    normalized = (raw_path or "").replace("\\", "/")
    best_match = ""
    for suffix in _SOURCE_SUFFIXES:
        index = normalized.casefold().find(suffix)
        if index == -1:
            continue
        candidate = normalized[: index + len(suffix)]
        if len(candidate) > len(best_match):
            best_match = candidate
    return best_match or normalized


def _sanitize_relative_candidate(raw_path: str) -> str:
    """Normalize relative path prefixes into a stable candidate value."""
    candidate = _trim_to_source_suffix(raw_path).replace("\\", "/").strip()
    while candidate.startswith("./"):
        candidate = candidate[2:]
    while candidate.startswith("../"):
        candidate = candidate[3:]
    return candidate


def _build_repo_file_indexes(repo_root: Path) -> _RepoFileIndexes:
    """Index repository files by basename and casefolded relative path."""
    by_name: Dict[str, List[str]] = {}
    casefold_paths: Dict[str, str] = {}
    resolved_root = repo_root.resolve(strict=False)

    for path in resolved_root.rglob("*"):
        try:
            if not path.is_file():
                continue
        except OSError:
            continue

        relative = path.relative_to(resolved_root).as_posix()
        casefold_paths[relative.casefold()] = relative
        by_name.setdefault(path.name, []).append(relative)

    return _RepoFileIndexes(
        repo_root=resolved_root,
        by_name=by_name,
        casefold_paths=casefold_paths,
    )


def _matching_repo_suffix(raw_path: str, casefold_paths: Dict[str, str]) -> str:
    """Return the best-matching repository suffix for an arbitrary input path."""
    candidate = _sanitize_relative_candidate(raw_path)
    candidate_casefold = candidate.casefold()
    if candidate_casefold in casefold_paths:
        return casefold_paths[candidate_casefold]

    best_match = ""
    for casefold_path, canonical in casefold_paths.items():
        if (
            candidate_casefold.endswith(casefold_path)
            and len(canonical) > len(best_match)
        ):
            best_match = canonical
    return best_match or candidate


def _normalize_source_path(raw_path: str, *, repo_indexes: _RepoFileIndexes) -> str:
    """Normalize LCOV source-file paths to repository-relative paths when possible."""
    candidate = (raw_path or "").replace("\\", "/").strip()
    if not candidate:
        return ""

    repo_root = repo_indexes.repo_root.as_posix().rstrip("/")
    if candidate == repo_root:
        return ""
    if candidate.startswith(repo_root + "/"):
        candidate = candidate[len(repo_root) + 1 :]

    matched = _matching_repo_suffix(candidate, repo_indexes.casefold_paths)
    if matched.casefold() in repo_indexes.casefold_paths:
        return repo_indexes.casefold_paths[matched.casefold()]

    basename = PurePosixPath(matched).name
    basename_matches = repo_indexes.by_name.get(basename) or []
    if len(basename_matches) == 1:
        return basename_matches[0]

    return matched


def _handle_da_line(line: str, *, kept_lines: List[str], record: _RecordState) -> None:
    """Append a DA line and accumulate totals for active normalized records."""
    kept_lines.append(line)
    if not record.active:
        return

    _, raw_payload = line.split(":", 1)
    line_number, hits, *_ = raw_payload.split(",")
    try:
        int(line_number)
        hit_count = int(hits)
    except ValueError:
        return

    record.total += 1
    if hit_count > 0:
        record.covered += 1


def _handle_sf_line(
    line: str,
    *,
    kept_lines: List[str],
    repo_indexes: _RepoFileIndexes,
) -> _RecordState:
    """Normalize an LCOV source-file line and return the next record state."""
    normalized_path = _normalize_source_path(
        line.split(":", 1)[1],
        repo_indexes=repo_indexes,
    )
    kept_lines.append(f"SF:{normalized_path}")
    return _RecordState(active=bool(normalized_path))


def _handle_record_metadata(
    line: str,
    *,
    kept_lines: List[str],
    record: _RecordState,
    synthesize_totals: bool,
) -> _RecordState | None:
    """Handle per-record metadata lines and return an updated state when matched."""
    if line.startswith("LF:"):
        kept_lines.append(line)
        record.saw_lf = True
        return record

    if line.startswith("LH:"):
        kept_lines.append(line)
        record.saw_lh = True
        return record

    if line != "end_of_record":
        return None

    _flush_record(
        kept_lines,
        record,
        synthesize_totals=synthesize_totals,
    )
    return _RecordState()


def _needs_trailing_record_flush(record: _RecordState, *, synthesize_totals: bool) -> bool:
    """Return whether the final unterminated record still needs synthesized totals."""
    return synthesize_totals and record.active and (
        record.total > 0 or record.saw_lf or record.saw_lh
    )


def _append_trailing_record_totals(
    *,
    kept_lines: List[str],
    record: _RecordState,
) -> None:
    """Append trailing LF/LH totals when the last record lacks an end marker."""
    if not record.saw_lf and record.total > 0:
        kept_lines.append(f"LF:{record.total}")
    if not record.saw_lh and record.total > 0:
        kept_lines.append(f"LH:{record.covered}")


def _flush_record(
    kept_lines: List[str],
    record: _RecordState,
    *,
    synthesize_totals: bool,
) -> None:
    """Append synthesized LF/LH totals when a record omitted them."""
    if synthesize_totals and record.active and record.total > 0:
        if not record.saw_lf:
            kept_lines.append(f"LF:{record.total}")
        if not record.saw_lh:
            kept_lines.append(f"LH:{record.covered}")
    kept_lines.append("end_of_record")


def normalize_lcov_lines(
    lines: Iterable[str],
    *,
    repo_root: Path | None = None,
) -> Tuple[str, int]:
    """Return LCOV text with branch records removed and count how many were stripped."""
    resolved_root = (repo_root or Path.cwd()).resolve(strict=False)
    synthesize_totals = repo_root is not None
    repo_indexes = _build_repo_file_indexes(resolved_root)
    kept_lines: List[str] = []
    stripped_count = 0
    record = _RecordState()

    for raw_line in lines:
        if raw_line.startswith(_BRANCH_PREFIXES):
            stripped_count += 1
            continue

        if raw_line.startswith("SF:"):
            record = _handle_sf_line(
                raw_line,
                kept_lines=kept_lines,
                repo_indexes=repo_indexes,
            )
            continue

        if raw_line.startswith("DA:"):
            _handle_da_line(raw_line, kept_lines=kept_lines, record=record)
            continue

        updated_record = _handle_record_metadata(
            raw_line,
            kept_lines=kept_lines,
            record=record,
            synthesize_totals=synthesize_totals,
        )
        if updated_record is not None:
            record = updated_record
            continue

        kept_lines.append(raw_line)

    if _needs_trailing_record_flush(record, synthesize_totals=synthesize_totals) and (
        not kept_lines or kept_lines[-1] != "end_of_record"
    ):
        _append_trailing_record_totals(
            kept_lines=kept_lines,
            record=record,
        )

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
    """Normalize LCOV from stdin to stdout and report stripped lines on stderr."""
    input_stream = stdin or sys.stdin
    output_stream = stdout or sys.stdout
    error_stream = stderr or sys.stderr

    raw_lines = input_stream.read().splitlines()
    normalize_kwargs = (
        {"repo_root": Path.cwd()}
        if raw_lines and raw_lines[-1] != "end_of_record"
        else {}
    )
    normalized, stripped_count = normalize_lcov_lines(
        raw_lines,
        **normalize_kwargs,
    )
    output_stream.write(normalized)
    error_stream.write(f"Normalized LCOV: stripped {stripped_count} branch records\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
