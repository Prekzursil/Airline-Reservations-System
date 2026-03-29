"""Shared validation and HTTPS helpers for repository quality scripts."""

from __future__ import absolute_import, annotations, division

import base64
import string
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, FrozenSet, Optional, Set, Tuple
from urllib.parse import urlparse, urlunparse

Headers = Dict[str, str]

_SAFE_REPO_SEGMENT_CHARS: FrozenSet[str] = frozenset(
    string.ascii_letters + string.digits + "._-"
)
_SAFE_SLUG_CHARS: FrozenSet[str] = frozenset(
    string.ascii_letters + string.digits + "._:-"
)
_SAFE_PATH_SEGMENT_CHARS: FrozenSet[str] = frozenset(
    string.ascii_letters + string.digits + "._-"
)
_SAFE_OUTPUT_NAME_CHARS: FrozenSet[str] = frozenset(
    string.ascii_letters + string.digits + "._-"
)
_HEX_CHARS: FrozenSet[str] = frozenset(string.hexdigits)
_HOST_CHARS: FrozenSet[str] = frozenset(string.ascii_lowercase + string.digits + ".-")
_JSON_CONTENT_TYPE = "application/json"
_SAFE_HEADER_NAME_CHARS: FrozenSet[str] = frozenset(
    string.ascii_letters + string.digits + "-"
)
_ALLOWED_HTTPS_HOSTS: FrozenSet[str] = frozenset(
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


_QUALITY_ARTIFACT_LAYOUT: Dict[QualityArtifact, Tuple[str, str, str]] = {
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


def _validation_module():
    """Import the validation support module lazily to avoid circular imports."""
    from scripts import security_validation_support

    return security_validation_support


def _http_module():
    """Import the HTTP support module lazily to avoid circular imports."""
    from scripts import security_http_support

    return security_http_support


def _require_identifier(raw: str, *, rules: IdentifierRules) -> str:
    """Validate a simple identifier against length and character constraints."""
    return _validation_module()._require_identifier(raw, rules=rules)


def normalize_https_url(
    raw_url: str,
    *,
    allowed_hosts: Optional[Set[str]] = None,
    allowed_host_suffixes: Optional[Set[str]] = None,
    strip_query: bool = False,
) -> str:
    """Validate and normalize an HTTPS URL with optional query stripping."""
    normalized = _validation_module().normalize_https_url(
        raw_url,
        allowed_hosts=allowed_hosts,
        allowed_host_suffixes=allowed_host_suffixes,
    )
    if not strip_query:
        return normalized

    parsed = urlparse(normalized)
    return urlunparse(parsed._replace(query=""))


def require_allowed_https_host(
    raw_host: str,
    *,
    allowed_hosts: Optional[Set[str]] = None,
) -> str:
    """Validate and normalize an HTTPS host against the allowlist."""
    return _validation_module().require_allowed_https_host(
        raw_host,
        allowed_hosts=allowed_hosts,
    )


def require_https_path(raw_path: str) -> str:
    """Validate that a request target is a safe relative HTTPS path."""
    return _validation_module().require_https_path(raw_path)


def require_repo_slug(raw: str) -> Tuple[str, str]:
    """Validate and split an owner/repository slug."""
    return _validation_module().require_repo_slug(raw)


def require_repo_segment(raw: str, *, label: str) -> str:
    """Validate a repository path segment such as owner or repo name."""
    return _validation_module().require_repo_segment(raw, label=label)


def require_slug(raw: str, *, label: str) -> str:
    """Validate a generic slug used by external quality services."""
    return _validation_module().require_slug(raw, label=label)


def require_sha(raw: str) -> str:
    """Validate a Git commit SHA."""
    return _validation_module().require_sha(raw)


def quote_segment(value: str) -> str:
    """Quote a URL segment without preserving reserved characters."""
    return _validation_module().quote_segment(value)


def quote_path_segment(value: str, *, label: str) -> str:
    """Validate and quote a safe single URL path segment."""
    return _validation_module().quote_path_segment(value, label=label)


def fixed_output_paths(out_dir: str, json_name: str, md_name: str) -> Tuple[Path, Path]:
    """Build fixed artifact paths rooted under the current working directory."""
    return _validation_module().fixed_output_paths(out_dir, json_name, md_name)


def quality_artifact_paths(artifact: QualityArtifact) -> Tuple[Path, Path]:
    """Return the JSON and markdown paths for a known quality artifact."""
    return _validation_module().quality_artifact_paths(artifact)


def build_https_request_target(
    *,
    host: HTTPSHost,
    path: str,
) -> HTTPSRequestTarget:
    """Build a validated HTTPS request target from host and path inputs."""
    return _validation_module().build_https_request_target(host=host, path=path)


def _https_connection() -> Any:
    """Return the HTTPS connection factory from the standard library."""
    return _http_module()._https_connection()


def _normalized_http_method(method: str) -> str:
    """Normalize and validate a supported HTTP method."""
    return _http_module()._normalized_http_method(method)


def _safe_timeout_seconds(timeout: int) -> int:
    """Clamp timeout configuration to a narrow, safe integer range."""
    return _http_module()._safe_timeout_seconds(timeout)


def _merge_safe_headers(
    headers: Optional[Headers],
    *,
    include_json_content_type: bool,
) -> Headers:
    """Merge user headers into a validated default JSON header set."""
    return _http_module()._merge_safe_headers(
        headers,
        include_json_content_type=include_json_content_type,
    )


def request_json_https(
    *,
    host: str,
    path: str,
    options: Optional[HTTPSRequestOptions] = None,
) -> Dict[str, Any]:
    """Perform a JSON HTTPS request using raw host and path inputs."""
    return _http_module().request_json_https(host=host, path=path, options=options)


def request_json_https_target(
    *,
    target: HTTPSRequestTarget,
    options: Optional[HTTPSRequestOptions] = None,
) -> Dict[str, Any]:
    """Perform a JSON HTTPS request using a prevalidated request target."""
    return _http_module().request_json_https_target(target=target, options=options)


def request_json_list_https(
    *,
    host: str,
    path: str,
    options: Optional[HTTPSRequestOptions] = None,
) -> Tuple[list[Any], Dict[str, str]]:
    """Perform a JSON-list HTTPS request using raw host and path inputs."""
    return _http_module().request_json_list_https(host=host, path=path, options=options)


def request_json_list_https_target(
    *,
    target: HTTPSRequestTarget,
    options: Optional[HTTPSRequestOptions] = None,
) -> Tuple[list[Any], Dict[str, str]]:
    """Perform a JSON-list HTTPS request using a prevalidated request target."""
    return _http_module().request_json_list_https_target(
        target=target,
        options=options,
    )


def basic_auth_header(token: str) -> str:
    """Build a basic-auth header for token-based APIs that expect `token:`."""
    raw = f"{token}:".encode("utf-8")
    return "Basic " + base64.b64encode(raw).decode("ascii")
