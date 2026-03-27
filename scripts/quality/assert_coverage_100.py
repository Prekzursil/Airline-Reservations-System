#!/usr/bin/env python3
from __future__ import absolute_import, annotations, division

import argparse
from functools import lru_cache
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Tuple

from scripts.security_helpers import QualityArtifact, quality_artifact_paths

NODE_LCOV_PATH = Path("airline-gui/coverage/lcov.info")
NODE_SUMMARY_JSON_PATH = Path("airline-gui/coverage/coverage-summary.json")
NODE_FINAL_JSON_PATH = Path("airline-gui/coverage/coverage-final.json")
CPP_LCOV_PATH = Path("coverage/cpp/lcov.info")
NON_EXECUTABLE_LCOV_TOKENS = {"", "{", "}", "};"}
INLINE_EXCLUSION_MARKERS = ("GCOVR_EXCL_LINE", "LCOV_EXCL_LINE")
EXCLUSION_START_MARKERS = ("GCOVR_EXCL_START", "LCOV_EXCL_START")
EXCLUSION_STOP_MARKERS = ("GCOVR_EXCL_STOP", "LCOV_EXCL_STOP")
REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class CoverageStats:
    name: str
    path: str
    covered: int
    total: int
    branch_covered: int = 0
    branch_total: int = 0

    @property
    def percent(self) -> float:
        if self.total <= 0:
            return 100.0
        return (self.covered / self.total) * 100.0

    @property
    def branch_percent(self) -> float:
        if self.branch_total <= 0:
            return 100.0
        return (self.branch_covered / self.branch_total) * 100.0


@dataclass
class LcovState:
    total: int = 0
    covered: int = 0
    record_lines: Dict[int, int] | None = None
    fallback_total: int = 0
    fallback_covered: int = 0
    source_lines: Tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        if self.record_lines is None:
            self.record_lines = {}


REPO_SOURCE_LINES = {
    path.relative_to(REPO_ROOT).as_posix(): tuple(path.read_text(encoding="utf-8").splitlines())
    for path in REPO_ROOT.rglob("*")
    if path.is_file()
    and path.suffix in {".cpp", ".h", ".hpp", ".c", ".cc", ".py", ".js", ".jsx", ".ts", ".tsx"}
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Assert 100% coverage for known project components.")
    parser.add_argument("--require-cpp", action="store_true", help="Fail if C++ lcov report is missing.")
    parser.add_argument(
        "--branch-min-percent",
        type=float,
        default=None,
        help="Optional minimum required branch coverage percentage.",
    )
    return parser.parse_args()


def parse_lcov(name: str, path: Path) -> CoverageStats:
    state = LcovState()
    branch_total = 0
    branch_covered = 0

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("BRF:"):
            branch_total += _safe_int(line.split(":", 1)[1])
            continue
        if line.startswith("BRH:"):
            branch_covered += _safe_int(line.split(":", 1)[1])
            continue
        _process_lcov_line(state, line)

    _flush_lcov_record(state)

    return CoverageStats(
        name=name,
        path=str(path),
        covered=state.covered,
        total=state.total,
        branch_covered=branch_covered,
        branch_total=branch_total,
    )


def _process_lcov_line(state: LcovState, line: str) -> None:
    if line.startswith("SF:"):
        _flush_lcov_record(state)
        state.source_lines = _lookup_repo_source_lines(line.split(":", 1)[1])
        return

    if line.startswith("DA:"):
        _record_lcov_line(state.record_lines, state.source_lines, line)
        return

    if line.startswith("LF:"):
        state.fallback_total = int(line.split(":", 1)[1])
        return

    if line.startswith("LH:"):
        state.fallback_covered = int(line.split(":", 1)[1])
        return

    if line == "end_of_record":
        _flush_lcov_record(state)


def _flush_lcov_record(state: LcovState) -> None:
    if not ((state.record_lines or {}) or state.fallback_total or state.fallback_covered):
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


def _record_lcov_line(record_lines: Dict[int, int], source_lines: Tuple[str, ...] | None, line: str) -> None:
    line_number_text, hit_count_text, *_ = line[3:].split(",")
    line_number = _safe_int(line_number_text)
    hit_count = _safe_int(hit_count_text)
    if _include_lcov_line(source_lines, line_number):
        record_lines[line_number] = max(record_lines.get(line_number, 0), hit_count)


def _include_lcov_line(source_lines: Tuple[str, ...] | None, line_number: int) -> bool:
    if source_lines is None or line_number <= 0:
        return True

    if line_number > len(source_lines):
        return True

    if line_number in _excluded_line_numbers(source_lines):
        return False

    source_line = source_lines[line_number - 1].strip()
    return source_line not in NON_EXECUTABLE_LCOV_TOKENS


@lru_cache(maxsize=None)
def _excluded_line_numbers(source_lines: Tuple[str, ...]) -> frozenset[int]:
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

        if in_excluded_block or any(marker in source_line for marker in INLINE_EXCLUSION_MARKERS):
            excluded.add(line_number)

    return frozenset(excluded)


def _lookup_repo_source_lines(raw_path_text: str) -> Tuple[str, ...] | None:
    normalized = raw_path_text.replace("\\", "/")
    repo_prefix = REPO_ROOT.as_posix().rstrip("/") + "/"
    if normalized.startswith(repo_prefix):
        normalized = normalized[len(repo_prefix):]
    if normalized.startswith("repo/"):
        normalized = normalized[len("repo/"):]
    normalized = normalized.lstrip("./")

    relative_path = PurePosixPath(normalized)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        return None

    return REPO_SOURCE_LINES.get(relative_path.as_posix())


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def parse_istanbul_summary(name: str, path: Path) -> CoverageStats:
    data = json.loads(path.read_text(encoding="utf-8"))
    total_node = data.get("total", {})
    lines = total_node.get("lines", {}) if isinstance(total_node, dict) else {}
    branches = total_node.get("branches", {}) if isinstance(total_node, dict) else {}

    covered = _safe_int(lines.get("covered"))
    total = _safe_int(lines.get("total"))
    branch_covered = _safe_int(branches.get("covered"))
    branch_total = _safe_int(branches.get("total"))

    if total <= 0:
        statements = total_node.get("statements", {}) if isinstance(total_node, dict) else {}
        covered = _safe_int(statements.get("covered"))
        total = _safe_int(statements.get("total"))

    return CoverageStats(
        name=name,
        path=str(path),
        covered=covered,
        total=total,
        branch_covered=branch_covered,
        branch_total=branch_total,
    )


def parse_istanbul_final(name: str, path: Path) -> CoverageStats:
    data = json.loads(path.read_text(encoding="utf-8"))
    covered = 0
    total = 0
    branch_covered = 0
    branch_total = 0

    if not isinstance(data, dict):
        return CoverageStats(name=name, path=str(path), covered=0, total=0, branch_covered=0, branch_total=0)

    for file_cov in data.values():
        if not isinstance(file_cov, dict):
            continue
        statements = file_cov.get("s", {})
        if not isinstance(statements, dict):
            continue
        total += len(statements)
        covered += sum(1 for count in statements.values() if _safe_int(count) > 0)
        branches = file_cov.get("b", {})
        if isinstance(branches, dict):
            for counts in branches.values():
                if not isinstance(counts, list):
                    continue
                branch_total += len(counts)
                branch_covered += sum(1 for count in counts if _safe_int(count) > 0)

    return CoverageStats(
        name=name,
        path=str(path),
        covered=covered,
        total=total,
        branch_covered=branch_covered,
        branch_total=branch_total,
    )


def load_node_stats() -> CoverageStats:
    if NODE_LCOV_PATH.exists():
        return parse_lcov("node", NODE_LCOV_PATH)
    if NODE_SUMMARY_JSON_PATH.exists():
        return parse_istanbul_summary("node", NODE_SUMMARY_JSON_PATH)
    if NODE_FINAL_JSON_PATH.exists():
        return parse_istanbul_final("node", NODE_FINAL_JSON_PATH)
    raise SystemExit(
        "Node coverage report is missing. Expected one of: "
        f"{NODE_LCOV_PATH}, {NODE_SUMMARY_JSON_PATH}, {NODE_FINAL_JSON_PATH}"
    )


def _component_findings(stats: List[CoverageStats]) -> List[str]:
    findings: List[str] = []
    for item in stats:
        if item.percent >= 100.0:
            continue
        findings.append(f"{item.name} coverage below 100%: {item.percent:.2f}% ({item.covered}/{item.total})")
    return findings


def _combined_coverage(stats: List[CoverageStats]) -> Tuple[int, int, float]:
    combined_total = sum(item.total for item in stats)
    combined_covered = sum(item.covered for item in stats)
    combined_percent = 100.0 if combined_total <= 0 else (combined_covered / combined_total) * 100.0
    return combined_covered, combined_total, combined_percent


def _combined_branch_coverage(stats: List[CoverageStats]) -> Tuple[int, int, float]:
    combined_total = sum(item.branch_total for item in stats)
    combined_covered = sum(item.branch_covered for item in stats)
    combined_percent = 100.0 if combined_total <= 0 else (combined_covered / combined_total) * 100.0
    return combined_covered, combined_total, combined_percent


def _branch_findings(stats: List[CoverageStats], branch_min_percent: float | None) -> List[str]:
    if branch_min_percent is None:
        return []

    findings: List[str] = []
    branch_stats = [item for item in stats if item.branch_total > 0]
    missing_branch_stats = [item for item in stats if item.branch_total <= 0]
    findings.extend(
        f"{item.name} branch coverage data missing from {item.path}"
        for item in missing_branch_stats
    )
    for item in branch_stats:
        if item.branch_percent < branch_min_percent:
            findings.append(
                f"{item.name} branch coverage below {branch_min_percent:.2f}%: "
                f"{item.branch_percent:.2f}% ({item.branch_covered}/{item.branch_total})"
            )

    combined_covered, combined_total, combined_percent = _combined_branch_coverage(branch_stats)
    if combined_total > 0 and combined_percent < branch_min_percent:
        findings.append(
            f"combined branch coverage below {branch_min_percent:.2f}%: "
            f"{combined_percent:.2f}% ({combined_covered}/{combined_total})"
        )
    return findings


def evaluate(stats: List[CoverageStats], branch_min_percent: float | None = None) -> Tuple[str, List[str]]:
    findings = _component_findings(stats)
    combined_covered, combined_total, combined_percent = _combined_coverage(stats)
    if combined_percent < 100.0:
        findings.append(f"combined coverage below 100%: {combined_percent:.2f}% ({combined_covered}/{combined_total})")
    findings.extend(_branch_findings(stats, branch_min_percent))

    status = "pass" if not findings else "fail"
    return status, findings


def _render_md(payload: Dict[str, Any]) -> str:
    lines = [
        "# Coverage 100 Gate",
        "",
        f"- Status: `{payload['status']}`",
        f"- Timestamp (UTC): `{payload['timestamp_utc']}`",
        f"- Minimum required branch coverage: `{payload['branch_min_percent'] if payload['branch_min_percent'] is not None else 'disabled'}`",
        "",
        "## Components",
    ]

    for item in payload.get("components", []):
        lines.append(
            f"- `{item['name']}`: line=`{item['percent']:.2f}%` ({item['covered']}/{item['total']})"
            + (
                f", branch=`{item['branch_percent']:.2f}%` ({item['branch_covered']}/{item['branch_total']})"
                if item.get("branch_total", 0)
                else ""
            )
            + f" from `{item['path']}`"
        )

    if not payload.get("components"):
        lines.append("- None")

    lines.extend(["", "## Findings"])
    findings = payload.get("findings") or []
    if findings:
        lines.extend(f"- {finding}" for finding in findings)
    else:
        lines.append("- None")

    return "\n".join(lines) + "\n"


def main() -> int:
    args = _parse_args()

    stats: List[CoverageStats] = []

    stats.append(load_node_stats())

    if args.require_cpp:
        if not CPP_LCOV_PATH.exists():
            raise SystemExit(f"C++ coverage report is missing: {CPP_LCOV_PATH}")
        stats.append(parse_lcov("cpp", CPP_LCOV_PATH))
    elif CPP_LCOV_PATH.exists():
        stats.append(parse_lcov("cpp", CPP_LCOV_PATH))

    branch_min_percent = None if args.branch_min_percent is None else max(0.0, min(100.0, float(args.branch_min_percent)))
    status, findings = evaluate(stats, branch_min_percent=branch_min_percent)
    payload = {
        "status": status,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "branch_min_percent": branch_min_percent,
        "components": [
            {
                "name": item.name,
                "path": item.path,
                "covered": item.covered,
                "total": item.total,
                "percent": item.percent,
                "branch_covered": item.branch_covered,
                "branch_total": item.branch_total,
                "branch_percent": item.branch_percent,
            }
            for item in stats
        ],
        "findings": findings,
    }

    out_json, out_md = quality_artifact_paths(QualityArtifact.COVERAGE_100)
    out_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    out_md.write_text(_render_md(payload), encoding="utf-8")
    print(out_md.read_text(encoding="utf-8"), end="")

    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
