"""Shared validation and HTTPS helpers for repository quality scripts."""

from __future__ import absolute_import, annotations, division

import http.client
import ipaddress
import json
import string
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple
from urllib.parse import quote, urlparse, urlunparse

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


def _require_identifier(
    raw: str,
    *,
    label: str,
    allowed_chars: FrozenSet[str],
    min_len: int,
    max_len: int,
) -> str:
    """Validate a simple identifier against length and character constraints."""
    value = (raw or "").strip()
    if len(value) < min_len or len(value) > max_len:
        raise ValueError(f"Invalid {label}: {raw!r}")
    if any(ch not in allowed_chars for ch in value):
        raise ValueError(f"Invalid {label}: {raw!r}")
    return value


def _has_invalid_host_characters(host: str) -> bool:
    """Return whether a hostname contains characters outside the allowlist."""
    return any(ch not in _HOST_CHARS for ch in host)


def _has_empty_host_label(labels: List[str]) -> bool:
    """Return whether a hostname contains an empty dot-separated label."""
    return any(not label for label in labels)


def _has_invalid_hyphen_label(labels: List[str]) -> bool:
    """Return whether a hostname label starts or ends with a hyphen."""
    return any(label.startswith("-") or label.endswith("-") for label in labels)


def _normalize_host(raw_host: str) -> str:
    """Normalize and validate a hostname before any network request uses it."""
    host = (raw_host or "").strip().lower().strip(".")
    if not host:
        raise ValueError(f"Invalid HTTPS host: {raw_host!r}")
    if _has_invalid_host_characters(host):
        raise ValueError(f"Invalid HTTPS host: {raw_host!r}")
    if ".." in host:
        raise ValueError(f"Invalid HTTPS host: {raw_host!r}")
    labels = host.split(".")
    if _has_empty_host_label(labels):
        raise ValueError(f"Invalid HTTPS host: {raw_host!r}")
    if _has_invalid_hyphen_label(labels):
        raise ValueError(f"Invalid HTTPS host: {raw_host!r}")
    return host


def _validate_output_filename(name: str, *, label: str) -> str:
    """Validate a single output filename component."""
    value = (name or "").strip()
    if not value:
        raise ValueError(f"{label} is required")
    if value in {".", ".."}:
        raise ValueError(f"Invalid {label}: {name!r}")
    if "/" in value or "\\" in value:
        raise ValueError(f"{label} must not contain path separators: {name!r}")
    if any(ch not in _SAFE_OUTPUT_NAME_CHARS for ch in value):
        raise ValueError(f"Invalid {label}: {name!r}")
    return value


def _validate_output_directory(out_dir: str) -> Path:
    """Validate and normalize a relative output directory path."""
    raw = (out_dir or "").strip().replace("\\", "/")
    if not raw:
        raise ValueError("output directory is required")
    if raw.startswith("/"):
        raise ValueError(f"Output directory must be relative: {out_dir!r}")

    parts: List[str] = []
    for segment in raw.split("/"):
        if not segment:
            continue
        checked = _validate_output_filename(segment, label="output directory segment")
        parts.append(checked)

    if not parts:
        raise ValueError(f"Invalid output directory: {out_dir!r}")
    return Path(*parts)


def _validate_https_url_shape(raw_url: str) -> Tuple[Any, str]:
    """Validate the coarse structure of an HTTPS URL and return its hostname."""
    parsed = urlparse((raw_url or "").strip())
    if parsed.scheme != "https":
        raise ValueError(f"Only https URLs are allowed: {raw_url!r}")
    if not parsed.hostname:
        raise ValueError(f"URL is missing a hostname: {raw_url!r}")
    if parsed.username or parsed.password:
        raise ValueError(f"URL credentials are not allowed: {raw_url!r}")
    return parsed, _normalize_host(parsed.hostname)


def _normalize_host_set(hosts: Set[str]) -> Set[str]:
    """Normalize every hostname in an exact-match allowlist."""
    return {_normalize_host(host) for host in hosts}


def _normalize_suffix_allowlist(allowed_host_suffixes: Optional[Set[str]]) -> Set[str]:
    """Normalize an optional hostname-suffix allowlist."""
    if allowed_host_suffixes is None:
        return set()
    return {
        _normalize_host(str(suffix).strip("."))
        for suffix in allowed_host_suffixes
        if str(suffix).strip(".")
    }


def _is_hostname_allowed_by_suffix(hostname: str, suffixes: Set[str]) -> bool:
    """Return whether a hostname matches any allowed suffix exactly or by subdomain."""
    return any(
        hostname == suffix or hostname.endswith(f".{suffix}")
        for suffix in suffixes
    )


def _ensure_host_allowlist(
    hostname: str,
    *,
    allowed_hosts: Optional[Set[str]] = None,
    allowed_host_suffixes: Optional[Set[str]] = None,
) -> None:
    """Enforce exact and suffix-based hostname allowlists for a request."""
    if allowed_hosts is not None and hostname not in _normalize_host_set(allowed_hosts):
        raise ValueError(f"URL host is not in allowlist: {hostname}")

    suffixes = _normalize_suffix_allowlist(allowed_host_suffixes)
    if suffixes and not _is_hostname_allowed_by_suffix(hostname, suffixes):
        raise ValueError(f"URL host is not in suffix allowlist: {hostname}")


def _parse_ip_or_none(hostname: str) -> Optional[Any]:
    """Parse a hostname as an IP address when possible."""
    try:
        return ipaddress.ip_address(hostname)
    except ValueError:
        return None


def _is_private_or_local_address(ip_value: Any) -> bool:
    """Return whether an IP value points to a private or local destination."""
    return any(
        (
            ip_value.is_private,
            ip_value.is_loopback,
            ip_value.is_link_local,
            ip_value.is_reserved,
            ip_value.is_multicast,
        )
    )


def _reject_private_or_local_host(hostname: str) -> None:
    """Reject hosts that resolve directly to local or private addresses."""
    ip_value = _parse_ip_or_none(hostname)
    if ip_value is not None and _is_private_or_local_address(ip_value):
        raise ValueError(f"Private or local addresses are not allowed: {hostname}")

    if hostname in {"localhost", "localhost.localdomain"}:
        raise ValueError("Localhost URLs are not allowed.")


def normalize_https_url(
    raw_url: str,
    *,
    allowed_hosts: Optional[Set[str]] = None,
    allowed_host_suffixes: Optional[Set[str]] = None,
    strip_query: bool = False,
) -> str:
    """Validate user-provided URLs for CLI scripts.

    Rules:
    - https scheme only,
    - no embedded credentials,
    - reject localhost/private/link-local IP targets,
    - optional hostname allowlist,
    - optional hostname suffix allowlist.
    """
    parsed, hostname = _validate_https_url_shape(raw_url)
    _ensure_host_allowlist(
        hostname,
        allowed_hosts=allowed_hosts,
        allowed_host_suffixes=allowed_host_suffixes,
    )
    _reject_private_or_local_host(hostname)

    sanitized = parsed._replace(fragment="", params="")
    if strip_query:
        sanitized = sanitized._replace(query="")
    return urlunparse(sanitized)


def require_allowed_https_host(
    raw_host: str,
    *,
    allowed_hosts: Optional[Set[str]] = None,
) -> str:
    """Validate and normalize an HTTPS host against the allowlist."""
    hostname = _normalize_host(raw_host)
    _reject_private_or_local_host(hostname)

    normalized_allowlist = (
        _ALLOWED_HTTPS_HOSTS
        if allowed_hosts is None
        else {_normalize_host(item) for item in allowed_hosts}
    )
    if hostname not in normalized_allowlist:
        raise ValueError(f"URL host is not in allowlist: {hostname}")
    return hostname


def _validate_https_path_prefix(path: str, raw_path: str) -> None:
    """Validate the leading structure of an HTTPS request path."""
    if not path.startswith("/") or path.startswith("//"):
        raise ValueError(f"HTTPS path must start with a single '/': {raw_path!r}")
    if "://" in path:
        raise ValueError(f"HTTPS path must not include a URL scheme: {raw_path!r}")


def _has_control_characters(value: str) -> bool:
    """Return whether a string contains ASCII control characters."""
    return any(ord(ch) < 0x20 for ch in value)


def _validate_https_path_chars(path: str, raw_path: str) -> None:
    """Reject unsafe characters in an HTTPS request path."""
    if any(ch.isspace() for ch in path):
        raise ValueError(f"HTTPS path must not include whitespace: {raw_path!r}")
    if _has_control_characters(path):
        raise ValueError(
            f"HTTPS path must not include control characters: {raw_path!r}"
        )


def _validate_https_path_components(path: str, raw_path: str) -> None:
    """Reject host or scheme data embedded in a request path value."""
    parsed = urlparse(path)
    if parsed.scheme or parsed.netloc:
        raise ValueError(f"HTTPS path must not include host data: {raw_path!r}")


def require_https_path(raw_path: str) -> str:
    """Validate that a request target is a safe relative HTTPS path."""
    path = (raw_path or "").strip()
    _validate_https_path_prefix(path, raw_path)
    _validate_https_path_chars(path, raw_path)
    _validate_https_path_components(path, raw_path)
    return path


def require_repo_slug(raw: str) -> Tuple[str, str]:
    """Validate and split an owner/repository slug."""
    value = (raw or "").strip()
    if value.count("/") != 1:
        raise ValueError(f"Invalid repository slug: {raw!r}")
    owner, repo = value.split("/", 1)
    return (
        require_repo_segment(owner, label="repository owner"),
        require_repo_segment(repo, label="repository name"),
    )


def require_repo_segment(raw: str, *, label: str) -> str:
    """Validate a repository path segment such as owner or repo name."""
    return _require_identifier(
        raw,
        label=label,
        allowed_chars=_SAFE_REPO_SEGMENT_CHARS,
        min_len=1,
        max_len=100,
    )


def require_slug(raw: str, *, label: str) -> str:
    """Validate a generic slug used by external quality services."""
    return _require_identifier(
        raw,
        label=label,
        allowed_chars=_SAFE_SLUG_CHARS,
        min_len=1,
        max_len=120,
    )


def require_sha(raw: str) -> str:
    """Validate a Git commit SHA."""
    value = (raw or "").strip()
    if len(value) < 7 or len(value) > 40 or any(ch not in _HEX_CHARS for ch in value):
        raise ValueError(f"Invalid commit SHA: {raw!r}")
    return value


def quote_segment(value: str) -> str:
    """Quote a URL segment without preserving reserved characters."""
    return quote(value, safe="")


def quote_path_segment(value: str, *, label: str) -> str:
    """Validate and quote a safe single URL path segment."""
    checked = _require_identifier(
        value,
        label=label,
        allowed_chars=_SAFE_PATH_SEGMENT_CHARS,
        min_len=1,
        max_len=120,
    )
    return quote(checked, safe="")


def fixed_output_paths(out_dir: str, json_name: str, md_name: str) -> Tuple[Path, Path]:
    """Build fixed artifact paths rooted under the current working directory."""
    root = Path.cwd().resolve()
    safe_dir = _validate_output_directory(out_dir)
    safe_json = _validate_output_filename(json_name, label="JSON filename")
    safe_md = _validate_output_filename(md_name, label="Markdown filename")

    directory = root / safe_dir
    directory.mkdir(parents=True, exist_ok=True)

    out_json = (directory / safe_json).resolve()
    out_md = (directory / safe_md).resolve()

    try:
        out_json.relative_to(root)
        out_md.relative_to(root)
    except ValueError as exc:
        raise ValueError("Output path escaped repository root") from exc

    return out_json, out_md


def quality_artifact_paths(artifact: QualityArtifact) -> Tuple[Path, Path]:
    """Return the JSON and markdown paths for a known quality artifact."""
    out_dir, json_name, md_name = _QUALITY_ARTIFACT_LAYOUT[artifact]
    return fixed_output_paths(out_dir, json_name, md_name)


def build_https_request_target(
    *,
    host: HTTPSHost,
    path: str,
) -> HTTPSRequestTarget:
    """Build a validated HTTPS request target from host and path inputs."""
    safe_host = require_allowed_https_host(host.value)
    safe_path = require_https_path(path)
    return HTTPSRequestTarget(host=safe_host, path=safe_path)


def _https_connection() -> Any:
    """Return the HTTPS connection factory from the standard library."""
    https_connection_factory = getattr(http.client, "HTTPSConnection", None)
    if https_connection_factory is None:
        raise RuntimeError("HTTPSConnection is unavailable in this Python runtime")
    return https_connection_factory


def _normalized_http_method(method: str) -> str:
    """Normalize and validate a supported HTTP method."""
    normalized = str(method or "").strip().upper()
    if normalized not in {"DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"}:
        raise ValueError(f"Unsupported HTTP method: {method!r}")
    return normalized


def _safe_timeout_seconds(timeout: int) -> int:
    """Clamp timeout configuration to a narrow, safe integer range."""
    checked = int(timeout)
    if checked <= 0 or checked > 300:
        raise ValueError(f"Invalid timeout value: {timeout!r}")
    return checked


def _contains_control_characters(value: str) -> bool:
    """Return whether a header value contains control characters."""
    return any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in value)


def _validate_header_name(name: str) -> str:
    """Validate an outbound HTTP header name."""
    checked = str(name or "").strip()
    if not checked:
        raise ValueError("Header name cannot be empty")
    if any(ch not in _SAFE_HEADER_NAME_CHARS for ch in checked):
        raise ValueError(f"Invalid HTTP header name: {name!r}")
    return checked


def _validate_header_value(value: str, *, name: str) -> str:
    """Validate an outbound HTTP header value."""
    checked = str(value or "")
    if _contains_control_characters(checked):
        raise ValueError(f"Invalid HTTP header value for {name!r}")
    return checked


def _merge_safe_headers(
    headers: Optional[Headers],
    *,
    include_json_content_type: bool,
) -> Headers:
    """Merge user headers into a validated default JSON header set."""
    final_headers: Headers = {"Accept": _JSON_CONTENT_TYPE}
    if headers:
        for key, value in headers.items():
            safe_name = _validate_header_name(key)
            final_headers[safe_name] = _validate_header_value(value, name=safe_name)
    if include_json_content_type:
        final_headers.setdefault("Content-Type", _JSON_CONTENT_TYPE)
    return final_headers


def _request_https_payload(
    *,
    target: HTTPSRequestTarget,
    method: str,
    headers: Optional[Dict[str, str]],
    timeout: int,
    body: Optional[Dict[str, Any]] = None,
    allowed_hosts: Optional[Set[str]] = None,
) -> HTTPSResponsePayload:
    """Perform a validated HTTPS request and return normalized response data."""
    safe_host = require_allowed_https_host(target.host, allowed_hosts=allowed_hosts)
    safe_path = require_https_path(target.path)
    safe_method = _normalized_http_method(method)
    safe_timeout = _safe_timeout_seconds(timeout)

    payload = None
    include_content_type = body is not None
    if body is not None:
        payload = json.dumps(body).encode("utf-8")
    final_headers = _merge_safe_headers(
        headers,
        include_json_content_type=include_content_type,
    )

    # nosemgrep: validated allowlist host and path
    conn = _https_connection()(safe_host, timeout=safe_timeout)
    try:
        conn.request(safe_method, safe_path, body=payload, headers=final_headers)
        response = conn.getresponse()
        raw = response.read().decode("utf-8", errors="replace")
        response_headers = {str(k).lower(): str(v) for k, v in response.getheaders()}
    finally:
        conn.close()

    return HTTPSResponsePayload(
        host=safe_host,
        path=safe_path,
        status=response.status,
        reason=str(response.reason),
        body=raw,
        headers=response_headers,
    )


def _parse_json_response(raw: str, *, host: str, path: str) -> Any:
    """Decode a JSON response body and attach host/path context on failure."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON response body from {host}{path}") from exc


def request_json_https(
    *,
    host: str,
    path: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    body: Optional[Dict[str, Any]] = None,
    timeout: int = 30,
    allowed_hosts: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    """Perform a JSON HTTPS request using raw host and path inputs."""
    target = HTTPSRequestTarget(
        host=require_allowed_https_host(host, allowed_hosts=allowed_hosts),
        path=require_https_path(path),
    )
    return request_json_https_target(
        target=target,
        method=method,
        headers=headers,
        body=body,
        timeout=timeout,
        allowed_hosts=allowed_hosts,
    )


def request_json_https_target(
    *,
    target: HTTPSRequestTarget,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    body: Optional[Dict[str, Any]] = None,
    timeout: int = 30,
    allowed_hosts: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    """Perform a JSON HTTPS request using a prevalidated request target."""
    response = _request_https_payload(
        target=target,
        method=method,
        headers=headers,
        body=body,
        timeout=timeout,
        allowed_hosts=allowed_hosts,
    )
    if response.status >= 400:
        raise HTTPSRequestError(response.status, response.reason, response.body)

    parsed = _parse_json_response(response.body, host=response.host, path=response.path)
    if not isinstance(parsed, dict):
        raise RuntimeError("Expected JSON object response")
    return parsed


def request_json_list_https(
    *,
    host: str,
    path: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 30,
    allowed_hosts: Optional[Set[str]] = None,
) -> Tuple[List[Any], Dict[str, str]]:
    """Perform a JSON-list HTTPS request using raw host and path inputs."""
    target = HTTPSRequestTarget(
        host=require_allowed_https_host(host, allowed_hosts=allowed_hosts),
        path=require_https_path(path),
    )
    return request_json_list_https_target(
        target=target,
        method=method,
        headers=headers,
        timeout=timeout,
        allowed_hosts=allowed_hosts,
    )


def request_json_list_https_target(
    *,
    target: HTTPSRequestTarget,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 30,
    allowed_hosts: Optional[Set[str]] = None,
) -> Tuple[List[Any], Dict[str, str]]:
    """Perform a JSON-list HTTPS request using a prevalidated request target."""
    response = _request_https_payload(
        target=target,
        method=method,
        headers=headers,
        timeout=timeout,
        allowed_hosts=allowed_hosts,
    )
    if response.status >= 400:
        raise HTTPSRequestError(response.status, response.reason, response.body)

    parsed = _parse_json_response(response.body, host=response.host, path=response.path)
    if not isinstance(parsed, list):
        raise RuntimeError("Expected JSON list response")

    return parsed, response.headers
