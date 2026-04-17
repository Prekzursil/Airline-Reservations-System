"""Shared constants and dataclasses for repository security helper modules."""

from __future__ import absolute_import, annotations, division

import string
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, FrozenSet, Optional, Set, Tuple

Headers = Dict[str, str]

SAFE_REPO_SEGMENT_CHARS: FrozenSet[str] = frozenset(
    string.ascii_letters + string.digits + "._-"
)
SAFE_SLUG_CHARS: FrozenSet[str] = frozenset(
    string.ascii_letters + string.digits + "._:-"
)
SAFE_PATH_SEGMENT_CHARS: FrozenSet[str] = frozenset(
    string.ascii_letters + string.digits + "._-"
)
SAFE_OUTPUT_NAME_CHARS: FrozenSet[str] = frozenset(
    string.ascii_letters + string.digits + "._-"
)
HEX_CHARS: FrozenSet[str] = frozenset(string.hexdigits)
HOST_CHARS: FrozenSet[str] = frozenset(
    string.ascii_lowercase + string.digits + ".-"
)
JSON_CONTENT_TYPE = "application/json"
SAFE_HEADER_NAME_CHARS: FrozenSet[str] = frozenset(
    string.ascii_letters + string.digits + "-"
)
ALLOWED_HTTPS_HOSTS: FrozenSet[str] = frozenset(
    {
        "api.github.com",
        "api.codacy.com",
        "sentry.io",
        "sonarcloud.io",
    }
)


class HTTPSHost(str, Enum):
    """Allowlisted HTTPS hosts for quality-gate scripts."""

    GITHUB_API = "api.github.com"
    CODACY_API = "api.codacy.com"
    SENTRY = "sentry.io"
    SONARCLOUD = "sonarcloud.io"


class QualityArtifact(str, Enum):
    """Known output artifact bundles written by quality scripts."""

    COVERAGE_100 = "coverage-100"
    CODACY_ZERO = "codacy-zero"
    DEEPSCAN_ZERO = "deepscan-zero"
    QUALITY_SECRETS = "quality-secrets"
    REQUIRED_CHECKS = "quality-zero-gate"
    SENTRY_ZERO = "sentry-zero"
    SONAR_ZERO = "sonar-zero"


@dataclass(frozen=True)
class HTTPSRequestTarget:
    """Validated host and path pair for an HTTPS request."""

    host: str
    path: str


@dataclass(frozen=True)
class HTTPSResponsePayload:
    """Normalized HTTPS response payload returned by helper requests."""

    host: str
    path: str
    status: int
    reason: str
    body: str
    headers: Headers


@dataclass(frozen=True)
class IdentifierRules:
    """Validation rules for simple identifiers used in external service paths."""

    label: str
    allowed_chars: FrozenSet[str]
    min_len: int
    max_len: int


@dataclass(frozen=True)
class HTTPSRequestOptions:
    """Normalized HTTPS request options shared across quality scripts."""

    method: str = "GET"
    headers: Optional[Headers] = None
    body: Optional[Dict[str, Any]] = None
    timeout: int = 30
    allowed_hosts: Optional[Set[str]] = None


QUALITY_ARTIFACT_LAYOUT: Dict[QualityArtifact, Tuple[str, str, str]] = {
    QualityArtifact.COVERAGE_100: ("coverage-100", "coverage.json", "coverage.md"),
    QualityArtifact.CODACY_ZERO: ("codacy-zero", "codacy.json", "codacy.md"),
    QualityArtifact.DEEPSCAN_ZERO: ("deepscan-zero", "deepscan.json", "deepscan.md"),
    QualityArtifact.QUALITY_SECRETS: ("quality-secrets", "secrets.json", "secrets.md"),
    QualityArtifact.REQUIRED_CHECKS: (
        "quality-zero-gate",
        "required-checks.json",
        "required-checks.md",
    ),
    QualityArtifact.SENTRY_ZERO: ("sentry-zero", "sentry.json", "sentry.md"),
    QualityArtifact.SONAR_ZERO: ("sonar-zero", "sonar.json", "sonar.md"),
}


class HTTPSRequestError(RuntimeError):
    """Structured HTTPS request error with status metadata for retry logic."""

    def __init__(self, status: int, reason: str, body: str):
        """Store response metadata while keeping exception text concise."""
        self.status = status
        self.reason = reason
        self.body_preview = body[:400]
        super().__init__(
            f"HTTPS request failed: {status} {reason}; body={self.body_preview}"
        )
