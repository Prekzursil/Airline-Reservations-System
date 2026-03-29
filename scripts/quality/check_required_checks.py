#!/usr/bin/env python3
"""Wait for required GitHub contexts and assert they all succeed."""

from __future__ import absolute_import, annotations, division

import argparse
import json
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

from scripts.security_helpers import (
    HTTPSHost,
    HTTPSRequestError,
    HTTPSRequestOptions,
    HTTPSRequestTarget,
    QualityArtifact,
    build_https_request_target,
    quality_artifact_paths,
    quote_segment,
    request_json_https_target,
    require_repo_slug,
    require_sha,
)
from scripts.quality.github_contexts import collect_contexts
from scripts.quality.required_checks_support import (
    evaluate_required_contexts,
    has_check_runs_in_progress,
)


def _parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the required-checks gate."""
    parser = argparse.ArgumentParser(
        description=(
            "Wait for required GitHub check contexts and assert they are successful."
        )
    )
    parser.add_argument("--repo", required=True, help="owner/repo")
    parser.add_argument("--sha", required=True, help="commit SHA")
    parser.add_argument(
        "--required-context",
        action="append",
        default=[],
        help="Required context name",
    )
    parser.add_argument("--timeout-seconds", type=int, default=900)
    parser.add_argument("--poll-seconds", type=int, default=20)
    return parser.parse_args()


def _api_get(target: HTTPSRequestTarget, token: str) -> Dict[str, Any]:
    """Fetch JSON from GitHub with short retry handling for transient failures."""
    retries = 4
    delay_seconds = 2
    for attempt in range(1, retries + 1):
        try:
            return request_json_https_target(
                target=target,
                options=HTTPSRequestOptions(
                    method="GET",
                    headers={
                        "Accept": "application/vnd.github+json",
                        "Authorization": f"Bearer {token}",
                        "X-GitHub-Api-Version": "2022-11-28",
                        "User-Agent": "airline-quality-zero-gate",
                    },
                ),
            )
        except HTTPSRequestError as exc:
            retryable = exc.status in {429, 500, 502, 503, 504}
            if not retryable or attempt == retries:
                raise RuntimeError(
                    "GitHub API request failed: "
                    f"HTTP {exc.status}; body={exc.body_preview[:300]}"
                ) from exc
        except RuntimeError as exc:
            if attempt == retries:
                raise RuntimeError(f"GitHub API request failed: {exc}") from exc

        time.sleep(delay_seconds)
        delay_seconds *= 2

    raise RuntimeError(
        "GitHub API request exhausted retries"
    )  # pragma: no cover - defensive fallback


def _render_md(payload: Dict[str, Any]) -> str:
    """Render the required-context gate result as markdown."""
    lines = [
        "# Quality Zero Gate - Required Contexts",
        "",
        f"- Status: `{payload['status']}`",
        f"- Repo/SHA: `{payload['repo']}@{payload['sha']}`",
        f"- Timestamp (UTC): `{payload['timestamp_utc']}`",
        "",
        "## Missing contexts",
    ]

    missing = payload.get("missing") or []
    if missing:
        lines.extend(f"- `{name}`" for name in missing)
    else:
        lines.append("- None")

    lines.extend(["", "## Failed contexts"])
    failed = payload.get("failed") or []
    if failed:
        lines.extend(f"- {entry}" for entry in failed)
    else:
        lines.append("- None")

    return "\n".join(lines) + "\n"


def _build_commit_api_path(repo: str, sha: str) -> str:
    """Build the GitHub API path prefix for the target commit."""
    owner, name = require_repo_slug(repo)
    checked_sha = require_sha(sha)
    return (
        f"/repos/{quote_segment(owner)}/{quote_segment(name)}/"
        f"commits/{quote_segment(checked_sha)}"
    )


def _build_commit_api_target(
    repo: str,
    sha: str,
    resource_path: str,
) -> HTTPSRequestTarget:
    """Build a commit-scoped GitHub API request target."""
    return build_https_request_target(
        host=HTTPSHost.GITHUB_API,
        path=f"{_build_commit_api_path(repo, sha)}{resource_path}",
    )


def _fetch_check_payloads(
    repo: str,
    sha: str,
    token: str,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Fetch the check-run and status payloads for a commit."""
    check_runs = _api_get(
        _build_commit_api_target(repo, sha, "/check-runs?per_page=100"),
        token,
    )
    statuses = _api_get(_build_commit_api_target(repo, sha, "/status"), token)
    return check_runs, statuses


def _collect_payload(
    args: argparse.Namespace,
    required: List[str],
    token: str,
) -> Dict[str, Any]:
    """Poll GitHub until required contexts either pass or settle in a failed state."""
    deadline = time.time() + max(args.timeout_seconds, 1)
    final_payload: Dict[str, Any] | None = None

    while time.time() <= deadline:
        check_runs, statuses = _fetch_check_payloads(args.repo, args.sha, token)
        contexts = collect_contexts(check_runs, statuses)
        status, missing, failed = evaluate_required_contexts(required, contexts)

        final_payload = {
            "status": status,
            "repo": args.repo,
            "sha": args.sha,
            "required": required,
            "missing": missing,
            "failed": failed,
            "contexts": contexts,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        }

        if status == "pass":
            break

        if not missing and not has_check_runs_in_progress(contexts):
            break
        time.sleep(max(args.poll_seconds, 1))

    if final_payload is None:
        raise RuntimeError("No payload collected")
    return final_payload


def main() -> int:
    """Run the required-checks gate and write result artifacts."""
    args = _parse_args()
    token = (
        os.environ.get("GITHUB_TOKEN", "")
        or os.environ.get("GH_TOKEN", "")
    ).strip()
    required = [item.strip() for item in args.required_context if item.strip()]

    if not required:
        raise SystemExit("At least one --required-context is required")
    if not token:
        raise SystemExit("GITHUB_TOKEN or GH_TOKEN is required")

    final_payload = _collect_payload(args, required, token)

    out_json, out_md = quality_artifact_paths(QualityArtifact.REQUIRED_CHECKS)
    out_json.write_text(
        json.dumps(final_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    out_md.write_text(_render_md(final_payload), encoding="utf-8")
    print(out_md.read_text(encoding="utf-8"), end="")
    return 0 if final_payload["status"] == "pass" else 1


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    raise SystemExit(main())
