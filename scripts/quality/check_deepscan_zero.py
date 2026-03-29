#!/usr/bin/env python3
"""Assert that the DeepScan GitHub context completes successfully."""

from __future__ import absolute_import, annotations, division

import argparse
import json
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from scripts.security_helpers import (
    HTTPSHost,
    HTTPSRequestTarget,
    QualityArtifact,
    build_https_request_target,
    quality_artifact_paths,
    quote_segment,
    request_json_https_target,
    require_repo_slug,
    require_sha,
)

_PENDING_STATES = {"pending", ""}


def _parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the DeepScan zero gate."""
    parser = argparse.ArgumentParser(
        description="Assert DeepScan GitHub context is green for a commit."
    )
    parser.add_argument("--repo", required=True, help="owner/repo")
    parser.add_argument("--sha", required=True, help="commit SHA")
    parser.add_argument(
        "--required-context",
        default="DeepScan",
        help="Required DeepScan context name",
    )
    parser.add_argument(
        "--max-wait-seconds",
        type=int,
        default=180,
        help="Maximum wait for external DeepScan context to appear/complete.",
    )
    parser.add_argument(
        "--poll-interval-seconds",
        type=int,
        default=10,
        help="Polling interval while waiting for context readiness.",
    )
    return parser.parse_args()


def _build_commit_api_path(repo: str, sha: str) -> str:
    """Build the base commit API path for the target repository and SHA."""
    owner, name = require_repo_slug(repo)
    checked_sha = require_sha(sha)

    owner_q = quote_segment(owner)
    repo_q = quote_segment(name)
    sha_q = quote_segment(checked_sha)
    return f"/repos/{owner_q}/{repo_q}/commits/{sha_q}"


def _build_commit_api_target(
    repo: str,
    sha: str,
    resource_path: str,
) -> HTTPSRequestTarget:
    """Build a GitHub API request target for a commit-scoped resource."""
    return build_https_request_target(
        host=HTTPSHost.GITHUB_API,
        path=f"{_build_commit_api_path(repo, sha)}{resource_path}",
    )


def _api_get(target: HTTPSRequestTarget, token: str) -> Dict[str, Any]:
    """Fetch a JSON document from the GitHub API."""
    return request_json_https_target(
        target=target,
        method="GET",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "airline-deepscan-zero-gate",
        },
    )


def _context_name(value: Any) -> str:
    """Normalize a check context name into a trimmed string."""
    return str(value or "").strip()


def _build_context_entry(*, state: Any, conclusion: Any, source: str) -> Dict[str, str]:
    """Create a normalized context payload."""
    return {
        "state": str(state or ""),
        "conclusion": str(conclusion or ""),
        "source": source,
    }


def _collect_context_entries(
    items: List[Dict[str, Any]],
    *,
    name_field: str,
    state_field: str,
    conclusion_field: Optional[str],
    source: str,
) -> Dict[str, Dict[str, str]]:
    """Collect normalized context entries from a GitHub checks payload."""
    contexts: Dict[str, Dict[str, str]] = {}
    for item in items:
        name = _context_name(item.get(name_field))
        if not name:
            continue
        state = item.get(state_field)
        conclusion = state if conclusion_field is None else item.get(conclusion_field)
        contexts[name] = _build_context_entry(
            state=state,
            conclusion=conclusion,
            source=source,
        )
    return contexts


def _collect_contexts(
    check_runs_payload: Dict[str, Any],
    status_payload: Dict[str, Any],
) -> Dict[str, Dict[str, str]]:
    """Collect check-run and status contexts keyed by their display name."""
    check_run_items = [
        item
        for item in check_runs_payload.get("check_runs", []) or []
        if isinstance(item, dict)
    ]
    status_items = [
        item
        for item in status_payload.get("statuses", []) or []
        if isinstance(item, dict)
    ]
    contexts = _collect_context_entries(
        check_run_items,
        name_field="name",
        state_field="status",
        conclusion_field="conclusion",
        source="check_run",
    )
    contexts.update(
        _collect_context_entries(
            status_items,
            name_field="context",
            state_field="state",
            conclusion_field=None,
            source="status",
        )
    )
    return contexts


def _render_md(payload: Dict[str, Any]) -> str:
    lines = [
        "# DeepScan Zero Gate",
        "",
        f"- Status: `{payload['status']}`",
        f"- Repo/SHA: `{payload['repo']}@{payload['sha']}`",
        f"- Required context: `{payload['required_context']}`",
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


def _poll_or_timeout(now: float, deadline: float, poll_seconds: int) -> bool:
    if now < deadline:
        time.sleep(max(poll_seconds, 1))
        return True
    return False


def _pending_failure_message(required_context: str, observed: Dict[str, str]) -> str:
    source = observed.get("source")
    state = observed.get("state")
    conclusion = observed.get("conclusion")
    if source == "check_run":
        return f"{required_context} status is {state} (expected completed)"
    return f"{required_context} state is {conclusion or 'unknown'} (expected success)"


def _is_pending_context(observed: Dict[str, str]) -> bool:
    source = observed.get("source")
    if source == "check_run":
        return observed.get("state") != "completed"
    return observed.get("conclusion") in _PENDING_STATES


def _context_outcome(
    required_context: str,
    observed: Dict[str, str],
) -> Tuple[str, Optional[str]]:
    source = observed.get("source")
    conclusion = observed.get("conclusion")
    if source == "check_run":
        if conclusion == "success" and observed.get("state") == "completed":
            return "pass", None
        return (
            "fail",
            f"{required_context} conclusion is {conclusion} (expected success)",
        )
    if conclusion == "success":
        return "pass", None
    return "fail", f"{required_context} state is {conclusion} (expected success)"


def _run_deepscan_check(
    args: argparse.Namespace,
    token: str,
) -> Tuple[str, List[str], Optional[Dict[str, str]]]:
    check_runs_target = _build_commit_api_target(
        args.repo,
        args.sha,
        "/check-runs?per_page=100",
    )
    statuses_target = _build_commit_api_target(args.repo, args.sha, "/status")
    deadline = time.time() + max(args.max_wait_seconds, 0)
    findings: List[str] = []

    while True:
        check_runs = _api_get(check_runs_target, token)
        statuses = _api_get(statuses_target, token)
        observed = _collect_contexts(check_runs, statuses).get(args.required_context)

        if observed is None:
            if _poll_or_timeout(time.time(), deadline, args.poll_interval_seconds):
                continue
            findings.append(f"Missing required context: {args.required_context}")
            return "fail", findings, None

        if _is_pending_context(observed):
            if _poll_or_timeout(time.time(), deadline, args.poll_interval_seconds):
                continue
            findings.append(_pending_failure_message(args.required_context, observed))
            return "fail", findings, observed

        status, failure = _context_outcome(args.required_context, observed)
        if failure:
            findings.append(failure)
        return status, findings, observed


def main() -> int:
    """Run the DeepScan gate and write result artifacts."""
    args = _parse_args()
    token = (
        os.environ.get("GITHUB_TOKEN", "")
        or os.environ.get("GH_TOKEN", "")
    ).strip()
    if not token:
        raise SystemExit("GITHUB_TOKEN or GH_TOKEN is required")

    status, findings, observed = _run_deepscan_check(args, token)

    payload: Dict[str, Any] = {
        "status": status,
        "repo": args.repo,
        "sha": args.sha,
        "required_context": args.required_context,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "findings": findings,
        "observed_context": observed,
    }

    out_json, out_md = quality_artifact_paths(QualityArtifact.DEEPSCAN_ZERO)
    out_json.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    out_md.write_text(_render_md(payload), encoding="utf-8")
    print(out_md.read_text(encoding="utf-8"), end="")
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
