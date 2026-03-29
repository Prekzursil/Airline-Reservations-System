#!/usr/bin/env python3
"""Validate that quality-gate secrets and variables are configured."""

from __future__ import absolute_import, annotations, division

import argparse
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Set

from scripts.security_helpers import QualityArtifact, quality_artifact_paths

DEFAULT_REQUIRED_SECRETS = [
    "SONAR_TOKEN",
    "CODACY_API_TOKEN",
    "CODECOV_TOKEN",
    "SENTRY_AUTH_TOKEN",
]

DEFAULT_REQUIRED_VARS = [
    "SENTRY_ORG",
    "SENTRY_PROJECT",
]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate required quality-gate secrets/variables are configured."
    )
    parser.add_argument(
        "--required-secret",
        action="append",
        default=[],
        help="Additional required secret env var",
    )
    parser.add_argument(
        "--required-var",
        action="append",
        default=[],
        help="Additional required variable env var",
    )
    return parser.parse_args()


def _dedupe(items: List[str]) -> List[str]:
    seen: Set[str] = set()
    out: List[str] = []
    for item in items:
        key = str(item or "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


def _is_configured(name: str) -> bool:
    return name in os.environ


def _partition_presence(required: List[str]) -> Dict[str, List[str]]:
    missing = [name for name in required if not _is_configured(name)]
    present = [name for name in required if name not in missing]
    return {
        "missing": missing,
        "present": present,
    }


def evaluate_env(
    required_secrets: List[str],
    required_vars: List[str],
) -> Dict[str, List[str]]:
    """Return present and missing secret and variable names."""
    secrets = _partition_presence(required_secrets)
    vars_payload = _partition_presence(required_vars)
    return {
        "missing_secrets": secrets["missing"],
        "missing_vars": vars_payload["missing"],
        "present_secrets": secrets["present"],
        "present_vars": vars_payload["present"],
    }


def evaluate_env_counts(
    required_secrets: List[str],
    required_vars: List[str],
) -> Dict[str, Any]:
    """Return only pass/fail counts so artifacts avoid secret-derived details."""
    missing_secret_count = sum(
        1 for name in required_secrets if not _is_configured(name)
    )
    missing_var_count = sum(1 for name in required_vars if not _is_configured(name))
    return {
        "status": (
            "pass"
            if missing_secret_count == 0 and missing_var_count == 0
            else "fail"
        ),
        "missing_secret_count": missing_secret_count,
        "missing_var_count": missing_var_count,
    }


def _render_md(*, timestamp_utc: str) -> str:
    lines = [
        "# Quality Secrets Preflight",
        "",
        f"- Timestamp (UTC): `{timestamp_utc}`",
        "",
        "Artifacts intentionally omit secret-derived details.",
        "Use the process exit code and GitHub check result for pass/fail state.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    """Run the quality-secrets preflight and write sanitized artifacts."""
    args = _parse_args()
    required_secrets = _dedupe(
        DEFAULT_REQUIRED_SECRETS + list(args.required_secret or [])
    )
    required_vars = _dedupe(DEFAULT_REQUIRED_VARS + list(args.required_var or []))

    result = evaluate_env_counts(required_secrets, required_vars)
    status = str(result["status"])
    timestamp_utc = datetime.now(timezone.utc).isoformat()
    payload = {
        "artifact": "quality-secrets-preflight",
        "timestamp_utc": timestamp_utc,
        "details_omitted": True,
    }

    out_json, out_md = quality_artifact_paths(QualityArtifact.QUALITY_SECRETS)
    out_json.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    out_md.write_text(_render_md(timestamp_utc=timestamp_utc), encoding="utf-8")
    print(out_md.read_text(encoding="utf-8"), end="")

    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
