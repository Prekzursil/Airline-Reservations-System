#!/usr/bin/env python3
from __future__ import absolute_import, annotations, division

import argparse
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

from scripts.security_helpers import (
    QualityArtifact,
    quality_artifact_paths,
)
from scripts.quality.sentry_support import resolve_project_slug, run_sentry_check
from scripts.quality.sentry_targets import SentryConfig, build_project_issues_path

_SENTRY_ORG_LABEL = "Sentry org"
_SENTRY_PROJECT_LABEL = "Sentry project"
_SENTRY_USER_AGENT = "airline-sentry-zero-gate"
_SENTRY_CONFIG = SentryConfig(
    org_label=_SENTRY_ORG_LABEL,
    project_label=_SENTRY_PROJECT_LABEL,
    user_agent=_SENTRY_USER_AGENT,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Assert Sentry has zero unresolved issues for configured projects.")
    parser.add_argument("--org", default="", help="Sentry org slug (falls back to SENTRY_ORG env)")
    parser.add_argument(
        "--project",
        action="append",
        default=[],
        help="Project slug (repeatable, falls back to SENTRY_PROJECT_BACKEND/SENTRY_PROJECT_WEB env)",
    )
    parser.add_argument("--token", default="", help="Sentry auth token (falls back to SENTRY_AUTH_TOKEN env)")
    return parser.parse_args()


def _render_md(payload: Dict[str, Any]) -> str:
    lines = [
        "# Sentry Zero Gate",
        "",
        f"- Status: `{payload['status']}`",
        f"- Org: `{payload.get('org')}`",
        f"- Timestamp (UTC): `{payload['timestamp_utc']}`",
        "",
        "## Project results",
    ]

    for item in payload.get("projects", []):
        lines.append(f"- `{item['project']}` unresolved=`{item['unresolved']}`")

    if not payload.get("projects"):
        lines.append("- None")

    lines.extend(["", "## Findings"])
    findings = payload.get("findings") or []
    if findings:
        lines.extend(f"- {item}" for item in findings)
    else:
        lines.append("- None")

    return "\n".join(lines) + "\n"


def _build_project_issues_path(org: str, project: str) -> str:
    return build_project_issues_path(org, project, _SENTRY_CONFIG)


def _resolve_project_slug(org: str, project: str, token: str) -> Optional[str]:
    return resolve_project_slug(org, project, token, _SENTRY_CONFIG)


def main() -> int:
    args = _parse_args()

    try:
        status, org, project_results, findings = run_sentry_check(args, _SENTRY_CONFIG)
    except (RuntimeError, ValueError) as exc:  # pragma: no cover - network/runtime surface
        status = "fail"
        org = (args.org or os.environ.get("SENTRY_ORG", "")).strip()
        project_results = []
        findings = [f"Sentry API request failed: {exc}"]

    payload: Dict[str, Any] = {
        "status": status,
        "org": org,
        "projects": project_results,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "findings": findings,
    }

    out_json, out_md = quality_artifact_paths(QualityArtifact.SENTRY_ZERO)
    out_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    out_md.write_text(_render_md(payload), encoding="utf-8")
    print(out_md.read_text(encoding="utf-8"), end="")
    return 0 if status == "pass" else 1


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    raise SystemExit(main())
