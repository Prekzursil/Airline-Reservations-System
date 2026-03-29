#!/usr/bin/env python3
"""Assert that Codacy reports zero open issues for a repository or branch."""

from __future__ import absolute_import, annotations, division

import argparse
import json
import os
import urllib.parse
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from scripts.security_helpers import (
    HTTPSHost,
    HTTPSRequestTarget,
    QualityArtifact,
    build_https_request_target,
    quality_artifact_paths,
    quote_path_segment,
    request_json_https_target,
    require_repo_segment,
)

TOTAL_KEYS = {"total", "totalItems", "total_items", "count", "hits", "open_issues"}
_ALLOWED_PROVIDERS = {"gh", "github"}


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the Codacy zero gate."""
    parser = argparse.ArgumentParser(
        description="Assert Codacy has zero total open issues."
    )
    parser.add_argument(
        "--provider",
        default="gh",
        help="Organization provider (gh/github).",
    )
    parser.add_argument("--owner", required=True, help="Repository owner")
    parser.add_argument("--repo", required=True, help="Repository name")
    parser.add_argument(
        "--branch",
        default="",
        help="Optional branch name to scope issue totals.",
    )
    parser.add_argument(
        "--token",
        default="",
        help="Codacy API token or the `CODACY_API_TOKEN` environment variable.",
    )
    return parser.parse_args()


def extract_total_open(payload: Any) -> Optional[int]:
    """Extract the first recognizable issue-total field from a nested payload."""
    nodes: List[Any] = [payload]
    while nodes:
        current = nodes.pop()
        if isinstance(current, dict):
            for key, value in current.items():
                if key in TOTAL_KEYS and isinstance(value, (int, float)):
                    return int(value)
            nodes.extend(current.values())
            continue
        if isinstance(current, list):
            nodes.extend(current)
    return None


def _render_md(payload: Dict[str, Any]) -> str:
    """Render the gate result as markdown."""
    lines = [
        "# Codacy Zero Gate",
        "",
        f"- Status: `{payload['status']}`",
        f"- Owner/repo: `{payload['owner']}/{payload['repo']}`",
        f"- Branch: `{payload.get('branch') or 'default'}`",
        f"- Open issues: `{payload.get('open_issues')}`",
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


def _build_issue_search_path(provider: str, owner: str, repo: str) -> str:
    """Build the Codacy API path used for the issue-total query."""
    provider_checked = (provider or "").strip().lower()
    if provider_checked not in _ALLOWED_PROVIDERS:
        raise ValueError(f"Unsupported provider: {provider}")

    owner_checked = require_repo_segment(owner, label="owner")
    repo_checked = require_repo_segment(repo, label="repo")

    provider_part = quote_path_segment(provider_checked, label="provider")
    owner_part = quote_path_segment(owner_checked, label="owner")
    repo_part = quote_path_segment(repo_checked, label="repo")
    query = urllib.parse.urlencode({"limit": "1"})

    return (
        f"/api/v3/analysis/organizations/{provider_part}/"
        f"{owner_part}/repositories/{repo_part}/issues/search?{query}"
    )


def _build_issue_search_target(
    provider: str,
    owner: str,
    repo: str,
) -> HTTPSRequestTarget:
    """Build the HTTPS request target for the Codacy issue search."""
    return build_https_request_target(
        host=HTTPSHost.CODACY_API,
        path=_build_issue_search_path(provider, owner, repo),
    )


def _resolve_token(token_arg: str) -> str:
    """Resolve the Codacy API token from args or environment."""
    return (token_arg or os.environ.get("CODACY_API_TOKEN", "")).strip()


def _fetch_open_issues(args: argparse.Namespace, token: str) -> Optional[int]:
    """Fetch the current Codacy open-issue total for the requested scope."""
    target = _build_issue_search_target(args.provider, args.owner, args.repo)
    body: Dict[str, str] = {}
    branch_name = (getattr(args, "branch", "") or "").strip()
    if branch_name:
        body["branchName"] = branch_name
    payload = request_json_https_target(
        target=target,
        method="POST",
        headers={
            "api-token": token,
            "User-Agent": "airline-codacy-zero-gate",
        },
        body=body,
    )
    return extract_total_open(payload)


def _evaluate_status(open_issues: Optional[int], findings: List[str]) -> str:
    """Convert the Codacy issue count into a pass/fail status."""
    if open_issues is None:
        findings.append(
            "Codacy response did not include a parseable total issue count."
        )
        return "fail"
    if open_issues != 0:
        findings.append(f"Codacy reports {open_issues} open issues (expected 0).")
        return "fail"
    return "pass"


def _run_codacy_check(
    args: argparse.Namespace,
    token: str,
) -> Tuple[Optional[int], List[str], str]:
    """Run the Codacy issue query and evaluate the result."""
    findings: List[str] = []
    open_issues: Optional[int] = None

    if not token:
        findings.append("CODACY_API_TOKEN is missing.")
        return open_issues, findings, "fail"

    try:
        open_issues = _fetch_open_issues(args, token)
        return open_issues, findings, _evaluate_status(open_issues, findings)
    except (
        RuntimeError,
        ValueError,
    ) as exc:  # pragma: no cover - network/runtime surface
        findings.append(f"Codacy API request failed: {exc}")
        return open_issues, findings, "fail"


def main() -> int:
    """Run the Codacy zero gate and write result artifacts."""
    args = _parse_args()
    token = _resolve_token(args.token)
    open_issues, findings, status = _run_codacy_check(args, token)

    payload: Dict[str, Any] = {
        "status": status,
        "owner": args.owner,
        "repo": args.repo,
        "provider": args.provider,
        "branch": args.branch,
        "open_issues": open_issues,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "findings": findings,
    }

    out_json, out_md = quality_artifact_paths(QualityArtifact.CODACY_ZERO)
    out_json.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    out_md.write_text(_render_md(payload), encoding="utf-8")
    print(out_md.read_text(encoding="utf-8"), end="")
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
