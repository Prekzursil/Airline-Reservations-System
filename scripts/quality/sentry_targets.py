#!/usr/bin/env python3
"""Sentry API target construction and configuration helpers."""

from __future__ import absolute_import, annotations, division

import urllib.parse
from dataclasses import dataclass
from typing import Dict, Optional

from scripts.security_helpers import (
    HTTPSHost,
    HTTPSRequestTarget,
    build_https_request_target,
    quote_path_segment,
    require_slug,
)


@dataclass(frozen=True)
class SentryConfig:
    """Configuration for a Sentry quality-gate check."""

    org_label: str
    project_label: str
    user_agent: str


def hits_from_headers(
    headers: Dict[str, str],
) -> Optional[int]:
    """Extract the X-Hits count from response headers."""
    raw = headers.get("x-hits")
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def auth_headers(
    token: str,
    config: SentryConfig,
) -> Dict[str, str]:
    """Build authentication headers for Sentry requests."""
    return {
        "Authorization": f"Bearer {token}",
        "User-Agent": config.user_agent,
    }


def build_project_issues_path(
    org: str,
    project: str,
    config: SentryConfig,
) -> str:
    """Build the API path for project issue queries."""
    org_slug = quote_path_segment(
        require_slug(org, label=config.org_label),
        label=config.org_label,
    )
    project_slug = quote_path_segment(
        require_slug(project, label=config.project_label),
        label=config.project_label,
    )
    query = urllib.parse.urlencode(
        {"query": "is:unresolved", "limit": "1"},
    )
    return f"/api/0/projects/{org_slug}/{project_slug}/issues/?{query}"


def build_project_issues_target(
    org: str,
    project: str,
    config: SentryConfig,
) -> HTTPSRequestTarget:
    """Build the HTTPS target for project issue queries."""
    return build_https_request_target(
        host=HTTPSHost.SENTRY,
        path=build_project_issues_path(org, project, config),
    )


def build_org_projects_target(
    org: str,
    project_query: str,
    config: SentryConfig,
) -> HTTPSRequestTarget:
    """Build the HTTPS target for organization project queries."""
    org_slug = quote_path_segment(
        require_slug(org, label=config.org_label),
        label=config.org_label,
    )
    query = urllib.parse.urlencode({"query": project_query})
    return build_https_request_target(
        host=HTTPSHost.SENTRY,
        path=f"/api/0/organizations/{org_slug}/projects/?{query}",
    )
