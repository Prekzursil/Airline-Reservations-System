#!/usr/bin/env python3
from __future__ import absolute_import, annotations, division

import argparse
import base64
import json
import os
import urllib.parse
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from scripts.security_helpers import (
    HTTPSHost,
    QualityArtifact,
    build_https_request_target,
    quality_artifact_paths,
    request_json_https_target,
    require_slug,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Assert SonarCloud has zero open issues and a passing quality gate.")
    parser.add_argument("--project-key", required=True, help="Sonar project key")
    parser.add_argument("--token", default="", help="Sonar token (falls back to SONAR_TOKEN env)")
    parser.add_argument("--branch", default="", help="Optional branch scope")
    parser.add_argument("--pull-request", default="", help="Optional PR scope")
    return parser.parse_args()


def _auth_header(token: str) -> str:
    raw = f"{token}:".encode("utf-8")
    return "Basic " + base64.b64encode(raw).decode("ascii")


def _render_md(payload: Dict[str, Any]) -> str:
    lines = [
        "# Sonar Zero Gate",
        "",
        f"- Status: `{payload['status']}`",
        f"- Project: `{payload['project_key']}`",
        f"- Open issues: `{payload.get('open_issues')}`",
        f"- Quality gate: `{payload.get('quality_gate')}`",
        f"- Timestamp (UTC): `{payload['timestamp_utc']}`",
        "",
        "## Findings",
    ]
    findings = payload.get("findings") or []
    if findings:
        lines.extend(f"- {item}" for item in findings)
    else:
        lines.append("- None")
    return "\n".join(lines) + "\n"


def _build_queries(args: argparse.Namespace, project_key: str) -> Tuple[Dict[str, str], Dict[str, str]]:
    issues_query: Dict[str, str] = {
        "componentKeys": project_key,
        "resolved": "false",
        "ps": "1",
    }
    gate_query: Dict[str, str] = {"projectKey": project_key}

    if args.branch:
        branch = require_slug(args.branch, label="Sonar branch")
        issues_query["branch"] = branch
        gate_query["branch"] = branch
    if args.pull_request:
        pr = require_slug(args.pull_request, label="Sonar pull request")
        issues_query["pullRequest"] = pr
        gate_query["pullRequest"] = pr

    return issues_query, gate_query


def _fetch_open_issues(auth: str, issues_query: Dict[str, str]) -> int:
    target = build_https_request_target(
        host=HTTPSHost.SONARCLOUD,
        path="/api/issues/search?" + urllib.parse.urlencode(issues_query),
    )
    issues_payload = request_json_https_target(
        target=target,
        method="GET",
        headers={
            "Authorization": auth,
            "User-Agent": "airline-sonar-zero-gate",
        },
    )
    paging = issues_payload.get("paging") or {}
    return int(paging.get("total") or 0)


def _fetch_quality_gate(auth: str, gate_query: Dict[str, str]) -> str:
    target = build_https_request_target(
        host=HTTPSHost.SONARCLOUD,
        path="/api/qualitygates/project_status?" + urllib.parse.urlencode(gate_query),
    )
    gate_payload = request_json_https_target(
        target=target,
        method="GET",
        headers={
            "Authorization": auth,
            "User-Agent": "airline-sonar-zero-gate",
        },
    )
    project_status = gate_payload.get("projectStatus") or {}
    return str(project_status.get("status") or "UNKNOWN")


def _evaluate_findings(open_issues: int, quality_gate: str) -> List[str]:
    findings: List[str] = []
    if open_issues != 0:
        findings.append(f"Sonar reports {open_issues} open issues (expected 0).")
    if quality_gate != "OK":
        findings.append(f"Sonar quality gate status is {quality_gate} (expected OK).")
    return findings


def _run_sonar_check(args: argparse.Namespace, token: str) -> Tuple[str, Optional[int], Optional[str], List[str]]:
    if not token:
        return "fail", None, None, ["SONAR_TOKEN is missing."]

    auth = _auth_header(token)
    project_key = require_slug(args.project_key, label="Sonar project key")
    issues_query, gate_query = _build_queries(args, project_key)

    open_issues = _fetch_open_issues(auth, issues_query)
    quality_gate = _fetch_quality_gate(auth, gate_query)
    findings = _evaluate_findings(open_issues, quality_gate)
    status = "pass" if not findings else "fail"
    return status, open_issues, quality_gate, findings


def main() -> int:
    args = _parse_args()
    token = (args.token or os.environ.get("SONAR_TOKEN", "")).strip()
    try:
        status, open_issues, quality_gate, findings = _run_sonar_check(args, token)
    except (RuntimeError, ValueError) as exc:  # pragma: no cover - network/runtime surface
        status = "fail"
        open_issues = None
        quality_gate = None
        findings = [f"Sonar API request failed: {exc}"]

    payload: Dict[str, Any] = {
        "status": status,
        "project_key": args.project_key,
        "open_issues": open_issues,
        "quality_gate": quality_gate,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "findings": findings,
    }

    out_json, out_md = quality_artifact_paths(QualityArtifact.SONAR_ZERO)
    out_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    out_md.write_text(_render_md(payload), encoding="utf-8")
    print(out_md.read_text(encoding="utf-8"), end="")

    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
