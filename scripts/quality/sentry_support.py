#!/usr/bin/env python3
from __future__ import absolute_import, annotations, division

import os
from typing import Any, Dict, List, Optional, Set, Tuple

from scripts.security_helpers import (
    HTTPSRequestOptions,
    request_json_list_https_target,
    require_slug,
)
from scripts.quality.sentry_targets import (
    SentryConfig,
    auth_headers,
    build_org_projects_target,
    build_project_issues_target,
    hits_from_headers,
)


def fetch_org_projects(
    org: str,
    project_query: str,
    token: str,
    config: SentryConfig,
) -> Optional[List[Any]]:
    target = build_org_projects_target(org, project_query, config)
    try:
        projects, _ = request_json_list_https_target(
            target=target,
            options=HTTPSRequestOptions(
                method="GET",
                headers=auth_headers(token, config),
            ),
        )
    except (RuntimeError, ValueError):
        return None
    return projects


def project_slug_from_match(item: Any, target: str) -> Optional[str]:
    if not isinstance(item, dict):
        return None
    slug = str(item.get("slug") or "").strip()
    name = str(item.get("name") or "").strip()
    if not slug:
        return None
    if slug.casefold() == target or name.casefold() == target:
        return slug
    return None


def resolve_project_slug(
    org: str,
    project: str,
    token: str,
    config: SentryConfig,
) -> Optional[str]:
    project_query = require_slug(project, label=config.project_label)
    projects = fetch_org_projects(
        org,
        project_query,
        token,
        config,
    )
    if projects is None:
        return None

    target = project_query.casefold()
    for item in projects:
        matched = project_slug_from_match(item, target)
        if matched:
            return matched
    return None


def project_candidates(
    org: str,
    project: str,
    token: str,
    config: SentryConfig,
) -> List[str]:
    candidates = [
        project,
        project.lower(),
        project.replace("_", "-"),
        project.replace("_", "-").lower(),
    ]
    resolved = resolve_project_slug(
        org,
        project,
        token,
        config,
    )
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


def is_not_found_error(exc: Exception) -> bool:
    message = str(exc)
    return "404" in message and "Not Found" in message


def projects_from_args_or_env(args: Any) -> List[str]:
    projects = [project for project in args.project if project]
    if projects:
        return projects

    env_projects: List[str] = []
    for env_name in ("SENTRY_PROJECT_BACKEND", "SENTRY_PROJECT_WEB", "SENTRY_PROJECT"):
        value = str(os.environ.get(env_name, "")).strip()
        if value:
            env_projects.append(value)
    return env_projects


def validate_inputs(token: str, org: str, projects: List[str]) -> List[str]:
    findings: List[str] = []
    if not token:
        findings.append("SENTRY_AUTH_TOKEN is missing.")
    if not org:
        findings.append("SENTRY_ORG is missing.")
    if not projects:
        findings.append("No Sentry projects configured.")
    return findings


def fetch_project_issues(
    org: str,
    project: str,
    token: str,
    config: SentryConfig,
) -> Tuple[List[Any], Dict[str, str]]:
    return request_json_list_https_target(
        target=build_project_issues_target(org, project, config),
        options=HTTPSRequestOptions(
            method="GET",
            headers=auth_headers(token, config),
        ),
    )


def select_project_payload(
    org: str,
    project: str,
    token: str,
    config: SentryConfig,
) -> Tuple[Optional[str], Optional[List[Any]], Dict[str, str], Optional[Exception]]:
    last_error: Optional[Exception] = None
    for candidate in project_candidates(
        org,
        project,
        token,
        config,
    ):
        try:
            issues, headers = fetch_project_issues(
                org,
                candidate,
                token,
                config,
            )
            return candidate, issues, headers, None
        except (RuntimeError, ValueError) as exc:  # pragma: no cover - network/runtime surface
            last_error = exc
            if is_not_found_error(exc):
                continue
            return None, None, {}, exc
    return None, None, {}, last_error


def unresolved_count(project: str, issues: List[Any], headers: Dict[str, str], findings: List[str]) -> int:
    unresolved = hits_from_headers(headers)
    if unresolved is not None:
        return unresolved

    unresolved = len(issues)
    if unresolved >= 1:
        findings.append(
            f"Sentry project {project} returned unresolved issues but no X-Hits header for exact totals."
        )
    return unresolved


def append_project_fetch_failure(project: str, last_error: Optional[Exception], org: str, findings: List[str]) -> None:
    if last_error is None:
        findings.append(f"Sentry project {project} did not return data.")
        return
    if is_not_found_error(last_error):
        findings.append(f"Sentry project {project} not found in org {org}.")
        return
    findings.append(f"Sentry project {project} request failed: {last_error}")


def evaluate_projects(
    org: str,
    projects: List[str],
    token: str,
    config: SentryConfig,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    findings: List[str] = []
    project_results: List[Dict[str, Any]] = []

    for project in projects:
        resolved_project, issues, headers, last_error = select_project_payload(
            org,
            project,
            token,
            config,
        )
        if issues is None:
            if last_error is not None and is_not_found_error(last_error):
                project_results.append(
                    {
                        "project": project,
                        "resolved_project": project,
                        "unresolved": 0,
                        "status": "not_found",
                    }
                )
                continue
            append_project_fetch_failure(project, last_error, org, findings)
            continue

        unresolved = unresolved_count(project, issues, headers, findings)
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


def run_sentry_check(
    args: Any,
    config: SentryConfig,
) -> Tuple[str, str, List[Dict[str, Any]], List[str]]:
    token = (args.token or os.environ.get("SENTRY_AUTH_TOKEN", "")).strip()
    org = (args.org or os.environ.get("SENTRY_ORG", "")).strip()
    projects = projects_from_args_or_env(args)

    findings = validate_inputs(token, org, projects)
    if findings:
        return "fail", org, [], findings

    project_results, project_findings = evaluate_projects(
        org,
        projects,
        token,
        config,
    )
    findings.extend(project_findings)
    status = "pass" if not findings else "fail"
    return status, org, project_results, findings
