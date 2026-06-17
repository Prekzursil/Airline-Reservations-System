"""Coverage parsing helpers shared by repository quality gates."""

from __future__ import absolute_import, annotations, division

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Tuple

NON_EXECUTABLE_LCOV_TOKENS = {"", "{", "}", "};"}
INLINE_EXCLUSION_MARKERS = ("GCOVR_EXCL_LINE", "LCOV_EXCL_LINE")
EXCLUSION_START_MARKERS = ("GCOVR_EXCL_START", "LCOV_EXCL_START")
EXCLUSION_STOP_MARKERS = ("GCOVR_EXCL_STOP", "LCOV_EXCL_STOP")
REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class CoverageStats:
    """Normalized covered and total counts for a named coverage component."""

    name: str
    path: str
    covered: int
    total: int

    @property
    def percent(self) -> float:
        """Return the covered percentage, treating empty totals as 100%."""
        if self.total <= 0:
            return 100.0
        return (self.covered / self.total) * 100.0


@dataclass
class LcovState:
    """Mutable state used while aggregating a single LCOV stream."""

    total: int = 0
    covered: int = 0
    record_lines: Dict[int, int] = field(default_factory=dict)
    fallback_total: int = 0
    fallback_covered: int = 0
    source_lines: Tuple[str, ...] | None = None


REPO_SOURCE_LINES = {
    path.relative_to(REPO_ROOT).as_posix(): tuple(
        path.read_text(encoding="utf-8").splitlines()
    )
    for path in REPO_ROOT.rglob("*")
    if path.is_file()
    and path.suffix
    in {".cpp", ".h", ".hpp", ".c", ".cc", ".py", ".js", ".jsx", ".ts", ".tsx"}
}


def parse_lcov(name: str, path: Path) -> CoverageStats:
    """Parse an LCOV report into aggregate covered and total line counts."""
    state = LcovState()
    for raw in path.read_text(encoding="utf-8").splitlines():
        _process_lcov_line(state, raw.strip())
    _flush_lcov_record(state)
    return CoverageStats(
        name=name,
        path=str(path),
        covered=state.covered,
        total=state.total,
    )


def _process_lcov_line(state: LcovState, line: str) -> None:
    """Update the current LCOV aggregation state from a single raw line."""
    if line.startswith("SF:"):
        _flush_lcov_record(state)
        state.source_lines = _lookup_repo_source_lines(line.split(":", 1)[1])
    elif line.startswith("DA:"):
        _record_lcov_line(state.record_lines, state.source_lines, line)
    elif line.startswith("LF:"):
        state.fallback_total = int(line.split(":", 1)[1])
    elif line.startswith("LH:"):
        state.fallback_covered = int(line.split(":", 1)[1])
    elif line == "end_of_record":
        _flush_lcov_record(state)


def _flush_lcov_record(state: LcovState) -> None:
    """Flush the current LCOV record into the aggregate running totals."""
    if not (
        (state.record_lines or {}) or state.fallback_total or state.fallback_covered
    ):
        return
    if state.record_lines:
        state.total += len(state.record_lines)
        state.covered += sum(1 for count in state.record_lines.values() if count > 0)
    else:
        state.total += state.fallback_total
        state.covered += state.fallback_covered
    state.record_lines = {}
    state.fallback_total = 0
    state.fallback_covered = 0


def _record_lcov_line(
    record_lines: Dict[int, int],
    source_lines: Tuple[str, ...] | None,
    line: str,
) -> None:
    """Record LCOV hit counts for executable source lines only."""
    line_number_text, hit_count_text, *_ = line[3:].split(",")
    line_number = _safe_int(line_number_text)
    hit_count = _safe_int(hit_count_text)
    if _include_lcov_line(source_lines, line_number):
        record_lines[line_number] = max(record_lines.get(line_number, 0), hit_count)


def _include_lcov_line(source_lines: Tuple[str, ...] | None, line_number: int) -> bool:
    """Return whether a reported LCOV line should count toward totals."""
    if source_lines is None or line_number <= 0 or line_number > len(source_lines):
        return True
    if line_number in _excluded_line_numbers(source_lines):
        return False
    source_line = source_lines[line_number - 1].strip()
    return source_line not in NON_EXECUTABLE_LCOV_TOKENS


@lru_cache(maxsize=None)
def _excluded_line_numbers(source_lines: Tuple[str, ...]) -> frozenset[int]:
    """Return source line numbers explicitly excluded from LCOV counting."""
    excluded = set()
    in_excluded_block = False
    for line_number, raw_line in enumerate(source_lines, start=1):
        source_line = raw_line.strip()
        if any(marker in source_line for marker in EXCLUSION_START_MARKERS):
            excluded.add(line_number)
            in_excluded_block = True
            continue
        if any(marker in source_line for marker in EXCLUSION_STOP_MARKERS):
            excluded.add(line_number)
            in_excluded_block = False
            continue
        if in_excluded_block or any(
            marker in source_line for marker in INLINE_EXCLUSION_MARKERS
        ):
            excluded.add(line_number)
    return frozenset(excluded)


def _lookup_repo_source_lines(raw_path_text: str) -> Tuple[str, ...] | None:
    """Resolve cached source lines for an LCOV path when it points into the repo."""
    normalized = raw_path_text.replace("\\", "/")
    repo_prefix = REPO_ROOT.as_posix().rstrip("/") + "/"
    if normalized.startswith(repo_prefix):
        normalized = normalized[len(repo_prefix) :]
    if normalized.startswith("repo/"):
        normalized = normalized[len("repo/") :]
    while normalized.startswith("./"):
        normalized = normalized[2:]
    relative_path = PurePosixPath(normalized)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        return None
    return REPO_SOURCE_LINES.get(relative_path.as_posix())


def include_lcov_line(
    source_lines: Tuple[str, ...] | None,
    line_number: int,
) -> bool:
    """Expose LCOV line filtering without relying on private module members."""
    return _include_lcov_line(source_lines, line_number)


def lookup_repo_source_lines(raw_path_text: str) -> Tuple[str, ...] | None:
    """Expose cached repository source lookup without private-member access."""
    return _lookup_repo_source_lines(raw_path_text)


def _safe_int(value: Any) -> int:
    """Convert a value to an integer and fall back to zero on invalid input."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def parse_istanbul_summary(name: str, path: Path) -> CoverageStats:
    """Parse line coverage totals from an Istanbul summary JSON artifact."""
    data = json.loads(path.read_text(encoding="utf-8"))
    total_node = data.get("total", {})
    lines = total_node.get("lines", {}) if isinstance(total_node, dict) else {}
    covered = _safe_int(lines.get("covered"))
    total = _safe_int(lines.get("total"))
    if total <= 0:
        statements = (
            total_node.get("statements", {}) if isinstance(total_node, dict) else {}
        )
        covered = _safe_int(statements.get("covered"))
        total = _safe_int(statements.get("total"))
    return CoverageStats(
        name=name,
        path=str(path),
        covered=covered,
        total=total,
    )


def parse_istanbul_final(name: str, path: Path) -> CoverageStats:
    """Parse statement hit totals from an Istanbul per-file JSON artifact."""
    data = json.loads(path.read_text(encoding="utf-8"))
    covered = 0
    total = 0
    if not isinstance(data, dict):
        return CoverageStats(name=name, path=str(path), covered=0, total=0)
    for file_cov in data.values():
        if not isinstance(file_cov, dict):
            continue
        statements = file_cov.get("s", {})
        if not isinstance(statements, dict):
            continue
        total += len(statements)
        covered += sum(1 for count in statements.values() if _safe_int(count) > 0)
    return CoverageStats(
        name=name,
        path=str(path),
        covered=covered,
        total=total,
    )
