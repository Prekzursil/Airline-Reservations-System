#!/usr/bin/env python3
"""Assert 100% coverage for the repository's required components."""

from __future__ import absolute_import, annotations, division

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

from scripts.security_helpers import QualityArtifact, quality_artifact_paths
from scripts.quality import coverage_parsers

CoverageStats = coverage_parsers.CoverageStats
REPO_SOURCE_LINES = coverage_parsers.REPO_SOURCE_LINES
_include_lcov_line = coverage_parsers.include_lcov_line
_lookup_repo_source_lines = coverage_parsers.lookup_repo_source_lines
parse_lcov = coverage_parsers.parse_lcov
parse_istanbul_summary = coverage_parsers.parse_istanbul_summary
parse_istanbul_final = coverage_parsers.parse_istanbul_final

NODE_LCOV_PATH = Path("airline-gui/coverage/lcov.info")
NODE_SUMMARY_JSON_PATH = Path("airline-gui/coverage/coverage-summary.json")
NODE_FINAL_JSON_PATH = Path("airline-gui/coverage/coverage-final.json")
CPP_LCOV_PATH = Path("coverage/cpp/lcov.info")


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the coverage gate."""
    parser = argparse.ArgumentParser(
        description="Assert 100% coverage for known project components."
    )
    parser.add_argument(
        "--require-cpp",
        action="store_true",
        help="Fail if C++ lcov report is missing.",
    )
    return parser.parse_args()


def load_node_stats() -> CoverageStats:
    """Load the preferred frontend coverage artifact."""
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
    """Return per-component findings for components below 100% coverage."""
    findings: List[str] = []
    for item in stats:
        if item.percent >= 100.0:
            continue
        findings.append(
            f"{item.name} coverage below 100%: "
            f"{item.percent:.2f}% ({item.covered}/{item.total})"
        )
    return findings


def _combined_coverage(stats: List[CoverageStats]) -> Tuple[int, int, float]:
    """Compute aggregate covered lines, total lines, and percentage."""
    combined_total = sum(item.total for item in stats)
    combined_covered = sum(item.covered for item in stats)
    combined_percent = (
        100.0
        if combined_total <= 0
        else (combined_covered / combined_total) * 100.0
    )
    return combined_covered, combined_total, combined_percent


def evaluate(stats: List[CoverageStats]) -> Tuple[str, List[str]]:
    """Evaluate component and combined coverage against a 100% target."""
    findings = _component_findings(stats)
    combined_covered, combined_total, combined_percent = _combined_coverage(stats)
    if combined_percent < 100.0:
        findings.append(
            "combined coverage below 100%: "
            f"{combined_percent:.2f}% ({combined_covered}/{combined_total})"
        )
    return ("pass" if not findings else "fail"), findings


def _render_md(payload: Dict[str, Any]) -> str:
    """Render the coverage gate result as markdown."""
    lines = [
        "# Coverage 100 Gate",
        "",
        f"- Status: `{payload['status']}`",
        f"- Timestamp (UTC): `{payload['timestamp_utc']}`",
        "",
        "## Components",
    ]

    components = payload.get("components") or []
    if components:
        for item in components:
            lines.append(
                "- "
                f"`{item['name']}`: "
                f"`{item['covered']}/{item['total']}` "
                f"(`{item['percent']:.2f}%`)"
            )
    else:
        lines.append("- None")

    lines.extend(["", "## Findings"])
    findings = payload.get("findings") or []
    if findings:
        lines.extend(f"- {item}" for item in findings)
    else:
        lines.append("- None")

    return "\n".join(lines) + "\n"


def main() -> int:
    """Run the coverage gate and write result artifacts."""
    args = _parse_args()
    stats: List[CoverageStats] = [load_node_stats()]

    if CPP_LCOV_PATH.exists():
        stats.append(parse_lcov("cpp", CPP_LCOV_PATH))
    elif args.require_cpp:
        raise SystemExit(f"C++ coverage report is missing: {CPP_LCOV_PATH}")

    status, findings = evaluate(stats)
    payload: Dict[str, Any] = {
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
    out_json.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    out_md.write_text(_render_md(payload), encoding="utf-8")
    print(out_md.read_text(encoding="utf-8"), end="")
    return 0 if status == "pass" else 1


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    raise SystemExit(main())
