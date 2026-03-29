"""Shared validation and HTTPS helpers for repository quality scripts."""

from __future__ import absolute_import, annotations, division

import base64
from pathlib import Path
from typing import Any, Dict, Optional, Set, Tuple
from urllib.parse import urlparse, urlunparse

from scripts.security_shared import (
    HTTPSHost,
    HTTPSRequestError,
    HTTPSRequestOptions,
    HTTPSRequestTarget,
    HTTPSResponsePayload,
    Headers,
    IdentifierRules,
    QualityArtifact,
    _ALLOWED_HTTPS_HOSTS,
    _HEX_CHARS,
    _HOST_CHARS,
    _JSON_CONTENT_TYPE,
    _QUALITY_ARTIFACT_LAYOUT,
    _SAFE_HEADER_NAME_CHARS,
    _SAFE_OUTPUT_NAME_CHARS,
    _SAFE_PATH_SEGMENT_CHARS,
    _SAFE_REPO_SEGMENT_CHARS,
    _SAFE_SLUG_CHARS,
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
    return _validation_module().require_identifier(raw, rules=rules)


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
    return _http_module().https_connection()


def _normalized_http_method(method: str) -> str:
    """Normalize and validate a supported HTTP method."""
    return _http_module().normalized_http_method(method)


def _safe_timeout_seconds(timeout: int) -> int:
    """Clamp timeout configuration to a narrow, safe integer range."""
    return _http_module().safe_timeout_seconds(timeout)


def _merge_safe_headers(
    headers: Optional[Headers],
    *,
    include_json_content_type: bool,
) -> Headers:
    """Merge user headers into a validated default JSON header set."""
    return _http_module().merge_safe_headers(
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
