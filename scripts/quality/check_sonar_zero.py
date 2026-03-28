#!/usr/bin/env python3
from __future__ import absolute_import, annotations, division

import argparse
import base64
import json
import os
import time
import urllib.parse
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from scripts.security_helpers import (
    HTTPSHost,
    HTTPSRequestOptions,
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
    parser.add_argument("--expected-pr-sha", default="", help="Expected analyzed PR head SHA")
    parser.add_argument("--max-wait-seconds", type=int, default=180, help="Maximum seconds to wait for Sonar PR analysis to catch up")
    parser.add_argument("--poll-interval-seconds", type=int, default=10, help="Seconds between Sonar PR analysis polls")
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
        f"- Unresolved security hotspots: `{payload.get('unresolved_security_hotspots')}`",
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


def _build_queries(args: argparse.Namespace, project_key: str) -> Tuple[Dict[str, str], Dict[str, str], Dict[str, str]]:
    issues_query: Dict[str, str] = {
        "componentKeys": project_key,
        "resolved": "false",
        "ps": "1",
    }
    gate_query: Dict[str, str] = {"projectKey": project_key}
    hotspots_query: Dict[str, str] = {
        "projectKey": project_key,
        "status": "TO_REVIEW",
        "ps": "1",
    }

    if args.branch:
        branch = require_slug(args.branch, label="Sonar branch")
        issues_query["branch"] = branch
        gate_query["branch"] = branch
        hotspots_query["branch"] = branch
    if args.pull_request:
        pr = require_slug(args.pull_request, label="Sonar pull request")
        issues_query["pullRequest"] = pr
        gate_query["pullRequest"] = pr
        hotspots_query["pullRequest"] = pr

    return issues_query, gate_query, hotspots_query


def _request_sonar_payload(auth: str, path: str) -> Dict[str, Any]:
    target = build_https_request_target(
        host=HTTPSHost.SONARCLOUD,
        path=path,
    )
    return request_json_https_target(
        target=target,
        options=HTTPSRequestOptions(
            method="GET",
            headers={
                "Authorization": auth,
                "User-Agent": "airline-sonar-zero-gate",
            },
        ),
    )


def _paged_total(payload: Dict[str, Any]) -> int:
    paging = payload.get("paging") or {}
    return int(paging.get("total") or 0)


def _fetch_open_issues(auth: str, issues_query: Dict[str, str]) -> int:
    return _paged_total(_request_sonar_payload(auth, "/api/issues/search?" + urllib.parse.urlencode(issues_query)))


def _fetch_quality_gate(auth: str, gate_query: Dict[str, str]) -> str:
    gate_payload = _request_sonar_payload(
        auth,
        "/api/qualitygates/project_status?" + urllib.parse.urlencode(gate_query),
    )
    project_status = gate_payload.get("projectStatus") or {}
    return str(project_status.get("status") or "UNKNOWN")


def _fetch_unresolved_hotspots(auth: str, hotspots_query: Dict[str, str]) -> int:
    hotspots_payload = _request_sonar_payload(
        auth,
        "/api/hotspots/search?" + urllib.parse.urlencode(hotspots_query),
    )
    return _paged_total(hotspots_payload)


def _fetch_pr_analysis_sha(auth: str, project_key: str, pull_request: str) -> str:
    payload = _request_sonar_payload(
        auth,
        "/api/project_pull_requests/list?" + urllib.parse.urlencode({"project": project_key}),
    )
    for item in payload.get("pullRequests") or []:
        if str(item.get("key") or "") == pull_request:
            commit = item.get("commit") or {}
            return str(commit.get("sha") or "")
    return ""


def _evaluate_findings(open_issues: int, unresolved_hotspots: int, quality_gate: str) -> List[str]:
    findings: List[str] = []
    if open_issues != 0:
        findings.append(f"Sonar reports {open_issues} open issues (expected 0).")
    if unresolved_hotspots != 0:
        findings.append(f"Sonar reports {unresolved_hotspots} unresolved security hotspots (expected 0).")
    if quality_gate != "OK":
        findings.append(f"Sonar quality gate status is {quality_gate} (expected OK).")
    return findings


def _run_sonar_check(args: argparse.Namespace, token: str) -> Tuple[str, Optional[int], Optional[int], Optional[str], List[str]]:
    if not token:
        return "fail", None, None, None, ["SONAR_TOKEN is missing."]

    auth = _auth_header(token)
    project_key = require_slug(args.project_key, label="Sonar project key")
    expected_pr_sha = args.expected_pr_sha.strip()
    if args.pull_request and expected_pr_sha:
        deadline = time.time() + max(args.max_wait_seconds, 0)
        observed_sha = ""
        while True:
            observed_sha = _fetch_pr_analysis_sha(auth, project_key, args.pull_request)
            if observed_sha == expected_pr_sha:
                break
            if time.time() >= deadline:
                return (
                    "fail",
                    None,
                    None,
                    None,
                    [
                        "Sonar PR analysis did not reach the expected head SHA before timeout.",
                        f"Expected SHA: {expected_pr_sha}",
                        f"Observed SHA: {observed_sha or 'missing'}",
                    ],
                )
            time.sleep(max(args.poll_interval_seconds, 1))

    issues_query, gate_query, hotspots_query = _build_queries(args, project_key)

    open_issues = _fetch_open_issues(auth, issues_query)
    unresolved_hotspots = _fetch_unresolved_hotspots(auth, hotspots_query)
    quality_gate = _fetch_quality_gate(auth, gate_query)
    findings = _evaluate_findings(open_issues, unresolved_hotspots, quality_gate)
    status = "pass" if not findings else "fail"
    return status, open_issues, unresolved_hotspots, quality_gate, findings


def main() -> int:
    args = _parse_args()
    token = (args.token or os.environ.get("SONAR_TOKEN", "")).strip()
    try:
        status, open_issues, unresolved_hotspots, quality_gate, findings = _run_sonar_check(args, token)
    except (RuntimeError, ValueError) as exc:  # pragma: no cover - network/runtime surface
        status = "fail"
        open_issues = None
        unresolved_hotspots = None
        quality_gate = None
        findings = [f"Sonar API request failed: {exc}"]

    payload: Dict[str, Any] = {
        "status": status,
        "project_key": args.project_key,
        "open_issues": open_issues,
        "unresolved_security_hotspots": unresolved_hotspots,
        "quality_gate": quality_gate,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "findings": findings,
    }

    out_json, out_md = quality_artifact_paths(QualityArtifact.SONAR_ZERO)
    out_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    out_md.write_text(_render_md(payload), encoding="utf-8")
    print(out_md.read_text(encoding="utf-8"), end="")

    return 0 if status == "pass" else 1


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    raise SystemExit(main())
