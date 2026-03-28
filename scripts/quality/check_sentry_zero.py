#!/usr/bin/env python3
"""Assert that configured Sentry projects have zero unresolved issues."""

from __future__ import absolute_import, annotations, division

import argparse
import json
import os
import urllib.parse
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from scripts.security_helpers import (
    HTTPSHost,
    HTTPSRequestTarget,
    QualityArtifact,
    build_https_request_target,
    quality_artifact_paths,
    quote_path_segment,
    request_json_list_https_target,
    require_slug,
)

_SENTRY_ORG_LABEL = "Sentry org"
_SENTRY_PROJECT_LABEL = "Sentry project"
_SENTRY_USER_AGENT = "airline-sentry-zero-gate"


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


def _hits_from_headers(headers: Dict[str, str]) -> Optional[int]:
    raw = headers.get("x-hits")
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


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
    org_slug = quote_path_segment(require_slug(org, label=_SENTRY_ORG_LABEL), label=_SENTRY_ORG_LABEL)
    project_slug = quote_path_segment(require_slug(project, label=_SENTRY_PROJECT_LABEL), label=_SENTRY_PROJECT_LABEL)
    query = urllib.parse.urlencode({"query": "is:unresolved", "limit": "1"})
    return f"/api/0/projects/{org_slug}/{project_slug}/issues/?{query}"


def _build_project_issues_target(org: str, project: str) -> HTTPSRequestTarget:
    return build_https_request_target(
        host=HTTPSHost.SENTRY,
        path=_build_project_issues_path(org, project),
    )


def _auth_headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "User-Agent": _SENTRY_USER_AGENT,
    }


def _build_org_projects_target(org: str, project_query: str) -> HTTPSRequestTarget:
    org_slug = quote_path_segment(require_slug(org, label=_SENTRY_ORG_LABEL), label=_SENTRY_ORG_LABEL)
    query = urllib.parse.urlencode({"query": project_query})
    return build_https_request_target(
        host=HTTPSHost.SENTRY,
        path=f"/api/0/organizations/{org_slug}/projects/?{query}",
    )


def _fetch_org_projects(org: str, project_query: str, token: str) -> Optional[List[Any]]:
    target = _build_org_projects_target(org, project_query)
    try:
        projects, _ = request_json_list_https_target(
            target=target,
            method="GET",
            headers=_auth_headers(token),
        )
    except (RuntimeError, ValueError):
        return None
    return projects


def _project_slug_from_match(item: Any, target: str) -> Optional[str]:
    if not isinstance(item, dict):
        return None
    slug = str(item.get("slug") or "").strip()
    name = str(item.get("name") or "").strip()
    if not slug:
        return None
    if slug.casefold() == target or name.casefold() == target:
        return slug
    return None


def _resolve_project_slug(org: str, project: str, token: str) -> Optional[str]:
    project_query = require_slug(project, label=_SENTRY_PROJECT_LABEL)
    projects = _fetch_org_projects(org, project_query, token)
    if projects is None:
        return None

    target = project_query.casefold()
    for item in projects:
        matched = _project_slug_from_match(item, target)
        if matched:
            return matched
    return None


def _project_candidates(org: str, project: str, token: str) -> List[str]:
    candidates = [
        project,
        project.lower(),
        project.replace("_", "-"),
        project.replace("_", "-").lower(),
    ]
    resolved = _resolve_project_slug(org, project, token)
    if resolved:
        candidates.insert(0, resolved)

    deduped: List[str] = []
    seen: Set[str] = set()
    for candidate in candidates:
        normalized = candidate.strip()
        if not normalized:
            continue
        key = normalized.casefold()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(normalized)
    return deduped


def _is_not_found_error(exc: Exception) -> bool:
    message = str(exc)
    return "404" in message and "Not Found" in message


def _projects_from_args_or_env(args: argparse.Namespace) -> List[str]:
    projects = [project for project in args.project if project]
    if projects:
        return projects

    env_projects: List[str] = []
    for env_name in ("SENTRY_PROJECT_BACKEND", "SENTRY_PROJECT_WEB", "SENTRY_PROJECT"):
        value = str(os.environ.get(env_name, "")).strip()
        if value:
            env_projects.append(value)
    return env_projects


def _validate_inputs(token: str, org: str, projects: List[str]) -> List[str]:
    findings: List[str] = []
    if not token:
        findings.append("SENTRY_AUTH_TOKEN is missing.")
    if not org:
        findings.append("SENTRY_ORG is missing.")
    if not projects:
        findings.append("No Sentry projects configured.")
    return findings


def _fetch_project_issues(org: str, project: str, token: str) -> Tuple[List[Any], Dict[str, str]]:
    return request_json_list_https_target(
        target=_build_project_issues_target(org, project),
        method="GET",
        headers=_auth_headers(token),
    )


def _select_project_payload(org: str, project: str, token: str) -> Tuple[Optional[str], Optional[List[Any]], Dict[str, str], Optional[Exception]]:
    last_error: Optional[Exception] = None
    for candidate in _project_candidates(org, project, token):
        try:
            issues, headers = _fetch_project_issues(org, candidate, token)
            return candidate, issues, headers, None
        except (RuntimeError, ValueError) as exc:  # pragma: no cover - network/runtime surface
            last_error = exc
            if _is_not_found_error(exc):
                continue
            return None, None, {}, exc
    return None, None, {}, last_error


def _unresolved_count(project: str, issues: List[Any], headers: Dict[str, str], findings: List[str]) -> int:
    unresolved = _hits_from_headers(headers)
    if unresolved is not None:
        return unresolved

    unresolved = len(issues)
    if unresolved >= 1:
        findings.append(
            f"Sentry project {project} returned unresolved issues but no X-Hits header for exact totals."
        )
    return unresolved


def _append_project_fetch_failure(project: str, last_error: Optional[Exception], org: str, findings: List[str]) -> None:
    if last_error is None:
        findings.append(f"Sentry project {project} did not return data.")
        return
    if _is_not_found_error(last_error):
        findings.append(f"Sentry project {project} not found in org {org}.")
        return
    findings.append(f"Sentry project {project} request failed: {last_error}")


def _evaluate_projects(org: str, projects: List[str], token: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    findings: List[str] = []
    project_results: List[Dict[str, Any]] = []

    for project in projects:
        resolved_project, issues, headers, last_error = _select_project_payload(org, project, token)
        if issues is None:
            if last_error is not None and _is_not_found_error(last_error):
                project_results.append(
                    {
                        "project": project,
                        "resolved_project": project,
                        "unresolved": 0,
                        "status": "not_found",
                    }
                )
                continue
            _append_project_fetch_failure(project, last_error, org, findings)
            continue

        unresolved = _unresolved_count(project, issues, headers, findings)
        if unresolved != 0:
            findings.append(f"Sentry project {project} has {unresolved} unresolved issues (expected 0).")

        project_results.append(
            {
                "project": project,
                "resolved_project": resolved_project or project,
                "unresolved": unresolved,
                "status": "ok",
            }
        )

    return project_results, findings


def _run_sentry_check(args: argparse.Namespace) -> Tuple[str, str, List[Dict[str, Any]], List[str]]:
    token = (args.token or os.environ.get("SENTRY_AUTH_TOKEN", "")).strip()
    org = (args.org or os.environ.get("SENTRY_ORG", "")).strip()
    projects = _projects_from_args_or_env(args)

    findings = _validate_inputs(token, org, projects)
    if findings:
        return "fail", org, [], findings

    project_results, project_findings = _evaluate_projects(org, projects, token)
    findings.extend(project_findings)
    status = "pass" if not findings else "fail"
    return status, org, project_results, findings


def main() -> int:
    """Run the Sentry zero gate and write result artifacts."""
    args = _parse_args()

    try:
        status, org, project_results, findings = _run_sentry_check(args)
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


if __name__ == "__main__":
    raise SystemExit(main())
