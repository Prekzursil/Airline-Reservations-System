#!/usr/bin/env python3
from __future__ import absolute_import, annotations, division

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

from scripts.security_helpers import QualityArtifact, quality_artifact_paths

NODE_LCOV_PATH = Path("airline-gui/coverage/lcov.info")
NODE_SUMMARY_JSON_PATH = Path("airline-gui/coverage/coverage-summary.json")
NODE_FINAL_JSON_PATH = Path("airline-gui/coverage/coverage-final.json")
CPP_LCOV_PATH = Path("coverage/cpp/lcov.info")
NON_EXECUTABLE_LCOV_TOKENS = {"", "{", "}", "};"}
REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class CoverageStats:
    name: str
    path: str
    covered: int
    total: int

    @property
    def percent(self) -> float:
        if self.total <= 0:
            return 100.0
        return (self.covered / self.total) * 100.0


@dataclass
class LcovState:
    total: int = 0
    covered: int = 0
    record_lines: Dict[int, int] | None = None
    fallback_total: int = 0
    fallback_covered: int = 0
    source_path: Path | None = None

    def __post_init__(self) -> None:
        if self.record_lines is None:
            self.record_lines = {}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Assert 100% coverage for known project components.")
    parser.add_argument("--require-cpp", action="store_true", help="Fail if C++ lcov report is missing.")
    return parser.parse_args()


def parse_lcov(name: str, path: Path) -> CoverageStats:
    state = LcovState()

    for raw in path.read_text(encoding="utf-8").splitlines():
        _process_lcov_line(state, raw.strip())

    _flush_lcov_record(state)

    return CoverageStats(name=name, path=str(path), covered=state.covered, total=state.total)


def _process_lcov_line(state: LcovState, line: str) -> None:
    if line.startswith("SF:"):
        _flush_lcov_record(state)
        state.source_path = Path(line.split(":", 1)[1])
        return

    if line.startswith("DA:"):
        _record_lcov_line(state.record_lines, state.source_path, line)
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


def _record_lcov_line(record_lines: Dict[int, int], source_path: Path | None, line: str) -> None:
    line_number_text, hit_count_text, *_ = line[3:].split(",")
    line_number = _safe_int(line_number_text)
    hit_count = _safe_int(hit_count_text)
    if _include_lcov_line(source_path, line_number):
        record_lines[line_number] = max(record_lines.get(line_number, 0), hit_count)


def _include_lcov_line(source_path: Path | None, line_number: int) -> bool:
    if source_path is None or line_number <= 0:
        return True

    safe_source_path = _resolve_repo_source_path(source_path)
    if safe_source_path is None:
        return True

    try:
        source_line = safe_source_path.read_text(encoding="utf-8").splitlines()[line_number - 1].strip()
    except (OSError, IndexError):
        return True

    return source_line not in NON_EXECUTABLE_LCOV_TOKENS


def _resolve_repo_source_path(source_path: Path) -> Path | None:
    candidate = source_path if source_path.is_absolute() else REPO_ROOT / source_path
    try:
        resolved = candidate.resolve()
        resolved.relative_to(REPO_ROOT)
    except (OSError, ValueError):
        return None

    return resolved


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def parse_istanbul_summary(name: str, path: Path) -> CoverageStats:
    data = json.loads(path.read_text(encoding="utf-8"))
    total_node = data.get("total", {})
    lines = total_node.get("lines", {}) if isinstance(total_node, dict) else {}

    covered = _safe_int(lines.get("covered"))
    total = _safe_int(lines.get("total"))

    if total <= 0:
        statements = total_node.get("statements", {}) if isinstance(total_node, dict) else {}
        covered = _safe_int(statements.get("covered"))
        total = _safe_int(statements.get("total"))

    return CoverageStats(name=name, path=str(path), covered=covered, total=total)


def parse_istanbul_final(name: str, path: Path) -> CoverageStats:
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

    return CoverageStats(name=name, path=str(path), covered=covered, total=total)


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


def evaluate(stats: List[CoverageStats]) -> Tuple[str, List[str]]:
    findings = _component_findings(stats)
    combined_covered, combined_total, combined_percent = _combined_coverage(stats)
    if combined_percent < 100.0:
        findings.append(f"combined coverage below 100%: {combined_percent:.2f}% ({combined_covered}/{combined_total})")

    status = "pass" if not findings else "fail"
    return status, findings


def _render_md(payload: Dict[str, Any]) -> str:
    lines = [
        "# Coverage 100 Gate",
        "",
        f"- Status: `{payload['status']}`",
        f"- Timestamp (UTC): `{payload['timestamp_utc']}`",
        "",
        "## Components",
    ]

    for item in payload.get("components", []):
        lines.append(
            f"- `{item['name']}`: `{item['percent']:.2f}%` ({item['covered']}/{item['total']}) from `{item['path']}`"
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

    status, findings = evaluate(stats)
    payload = {
        "status": status,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "components": [
            {
                "name": item.name,
                "path": item.path,
                "covered": item.covered,
                "total": item.total,
                "percent": item.percent,
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
