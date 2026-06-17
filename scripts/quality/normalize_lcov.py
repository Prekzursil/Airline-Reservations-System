#!/usr/bin/env python3
"""Strip branch records from LCOV input while preserving line coverage."""

from __future__ import absolute_import, annotations, division

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, TextIO, Tuple

from scripts.quality import lcov_path_support

_BRANCH_PREFIXES = ("BRDA:", "BRF:", "BRH:")
_RepoFileIndexes = lcov_path_support.RepoFileIndexes


@dataclass
class _RecordState:
    """Mutable per-record LCOV counters tracked during normalization."""

    active: bool = False
    total: int = 0
    covered: int = 0
    saw_lf: bool = False
    saw_lh: bool = False


@dataclass(frozen=True)
class _NormalizationContext:
    """Shared immutable context for a single LCOV normalization pass."""

    kept_lines: List[str]
    repo_indexes: _RepoFileIndexes
    synthesize_totals: bool


def _trim_to_source_suffix(raw_path: str) -> str:
    """Trim known LCOV suffix noise after a source filename."""
    return lcov_path_support.trim_to_source_suffix(raw_path)


def _sanitize_relative_candidate(raw_path: str) -> str:
    """Normalize relative path prefixes into a stable candidate value."""
    return lcov_path_support.sanitize_relative_candidate(raw_path)


def _build_repo_file_indexes(repo_root: Path) -> _RepoFileIndexes:
    """Index repository files by basename and casefolded relative path."""
    return lcov_path_support.build_repo_file_indexes(repo_root)


def _matching_repo_suffix(raw_path: str, casefold_paths: Dict[str, str]) -> str:
    """Return the best-matching repository suffix for an arbitrary input path."""
    return lcov_path_support.matching_repo_suffix(raw_path, casefold_paths)


def _normalize_source_path(raw_path: str, *, repo_indexes: _RepoFileIndexes) -> str:
    """Normalize LCOV source-file paths to repository-relative paths when possible."""
    return lcov_path_support.normalize_source_path(
        raw_path,
        repo_indexes=repo_indexes,
    )


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


def _needs_trailing_record_flush(
    record: _RecordState,
    *,
    synthesize_totals: bool,
) -> bool:
    """Return whether the final unterminated record still needs synthesized totals."""
    return (
        synthesize_totals
        and record.active
        and (record.total > 0 or record.saw_lf or record.saw_lh)
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


def _handle_non_branch_line(
    raw_line: str,
    record: _RecordState,
    context: _NormalizationContext,
) -> _RecordState:
    """Update LCOV record state for any non-branch line."""
    if raw_line.startswith("SF:"):
        return _handle_sf_line(
            raw_line,
            kept_lines=context.kept_lines,
            repo_indexes=context.repo_indexes,
        )

    if raw_line.startswith("DA:"):
        _handle_da_line(raw_line, kept_lines=context.kept_lines, record=record)
        return record

    updated_record = _handle_record_metadata(
        raw_line,
        kept_lines=context.kept_lines,
        record=record,
        synthesize_totals=context.synthesize_totals,
    )
    if updated_record is not None:
        return updated_record

    context.kept_lines.append(raw_line)
    return record


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
    context = _NormalizationContext(
        kept_lines=kept_lines,
        repo_indexes=repo_indexes,
        synthesize_totals=synthesize_totals,
    )
    stripped_count = 0
    record = _RecordState()

    for raw_line in lines:
        if raw_line.startswith(_BRANCH_PREFIXES):
            stripped_count += 1
            continue
        record = _handle_non_branch_line(
            raw_line,
            record=record,
            context=context,
        )

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


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    raise SystemExit(main())
