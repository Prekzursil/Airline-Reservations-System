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

_SAFE_REPO_SEGMENT_CHARS: FrozenSet[str] = frozenset(string.ascii_letters + string.digits + "._-")
_SAFE_SLUG_CHARS: FrozenSet[str] = frozenset(string.ascii_letters + string.digits + "._:-")
_SAFE_PATH_SEGMENT_CHARS: FrozenSet[str] = frozenset(string.ascii_letters + string.digits + "._-")
_SAFE_OUTPUT_NAME_CHARS: FrozenSet[str] = frozenset(string.ascii_letters + string.digits + "._-")
_HEX_CHARS: FrozenSet[str] = frozenset(string.hexdigits)
_HOST_CHARS: FrozenSet[str] = frozenset(string.ascii_lowercase + string.digits + ".-")
_JSON_CONTENT_TYPE = "application/json"
_ALLOWED_HTTPS_HOSTS: FrozenSet[str] = frozenset(
    {
        "api.github.com",
        "api.codacy.com",
        "sentry.io",
        "sonarcloud.io",
    }
)


class HTTPSHost(str, Enum):
    GITHUB_API = "api.github.com"
    CODACY_API = "api.codacy.com"
    SENTRY = "sentry.io"
    SONARCLOUD = "sonarcloud.io"


class QualityArtifact(str, Enum):
    COVERAGE_100 = "coverage-100"
    CODACY_ZERO = "codacy-zero"
    DEEPSCAN_ZERO = "deepscan-zero"
    QUALITY_SECRETS = "quality-secrets"
    REQUIRED_CHECKS = "quality-zero-gate"
    SENTRY_ZERO = "sentry-zero"
    SONAR_ZERO = "sonar-zero"


@dataclass(frozen=True)
class HTTPSRequestTarget:
    host: str
    path: str


_QUALITY_ARTIFACT_LAYOUT: Dict[QualityArtifact, Tuple[str, str, str]] = {
    QualityArtifact.COVERAGE_100: ("coverage-100", "coverage.json", "coverage.md"),
    QualityArtifact.CODACY_ZERO: ("codacy-zero", "codacy.json", "codacy.md"),
    QualityArtifact.DEEPSCAN_ZERO: ("deepscan-zero", "deepscan.json", "deepscan.md"),
    QualityArtifact.QUALITY_SECRETS: ("quality-secrets", "secrets.json", "secrets.md"),
    QualityArtifact.REQUIRED_CHECKS: ("quality-zero-gate", "required-checks.json", "required-checks.md"),
    QualityArtifact.SENTRY_ZERO: ("sentry-zero", "sentry.json", "sentry.md"),
    QualityArtifact.SONAR_ZERO: ("sonar-zero", "sonar.json", "sonar.md"),
}


class HTTPSRequestError(RuntimeError):
    """Structured HTTPS request error with status metadata for retry logic."""

    def __init__(self, status: int, reason: str, body: str):
        self.status = status
        self.reason = reason
        self.body_preview = body[:400]
        super().__init__(f"HTTPS request failed: {status} {reason}; body={self.body_preview}")


def _require_identifier(
    raw: str,
    *,
    label: str,
    allowed_chars: FrozenSet[str],
    min_len: int,
    max_len: int,
) -> str:
    value = (raw or "").strip()
    if len(value) < min_len or len(value) > max_len:
        raise ValueError(f"Invalid {label}: {raw!r}")
    if any(ch not in allowed_chars for ch in value):
        raise ValueError(f"Invalid {label}: {raw!r}")
    return value


def _has_invalid_host_characters(host: str) -> bool:
    return any(ch not in _HOST_CHARS for ch in host)


def _has_empty_host_label(labels: List[str]) -> bool:
    return any(not label for label in labels)


def _has_invalid_hyphen_label(labels: List[str]) -> bool:
    return any(label.startswith("-") or label.endswith("-") for label in labels)


def _normalize_host(raw_host: str) -> str:
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
    parsed = urlparse((raw_url or "").strip())
    if parsed.scheme != "https":
        raise ValueError(f"Only https URLs are allowed: {raw_url!r}")
    if not parsed.hostname:
        raise ValueError(f"URL is missing a hostname: {raw_url!r}")
    if parsed.username or parsed.password:
        raise ValueError(f"URL credentials are not allowed: {raw_url!r}")
    return parsed, _normalize_host(parsed.hostname)


def _normalize_host_set(hosts: Set[str]) -> Set[str]:
    return {_normalize_host(host) for host in hosts}


def _normalize_suffix_allowlist(allowed_host_suffixes: Optional[Set[str]]) -> Set[str]:
    if allowed_host_suffixes is None:
        return set()
    return {
        _normalize_host(str(suffix).strip("."))
        for suffix in allowed_host_suffixes
        if str(suffix).strip(".")
    }


def _is_hostname_allowed_by_suffix(hostname: str, suffixes: Set[str]) -> bool:
    for suffix in suffixes:
        if hostname == suffix or hostname.endswith(f".{suffix}"):
            return True
    return False


def _ensure_host_allowlist(
    hostname: str,
    *,
    allowed_hosts: Optional[Set[str]] = None,
    allowed_host_suffixes: Optional[Set[str]] = None,
) -> None:
    if allowed_hosts is not None and hostname not in _normalize_host_set(allowed_hosts):
        raise ValueError(f"URL host is not in allowlist: {hostname}")

    suffixes = _normalize_suffix_allowlist(allowed_host_suffixes)
    if suffixes and not _is_hostname_allowed_by_suffix(hostname, suffixes):
        raise ValueError(f"URL host is not in suffix allowlist: {hostname}")


def _parse_ip_or_none(hostname: str) -> Optional[Any]:
    try:
        return ipaddress.ip_address(hostname)
    except ValueError:
        return None


def _is_private_or_local_address(ip_value: Any) -> bool:
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


def require_allowed_https_host(raw_host: str, *, allowed_hosts: Optional[Set[str]] = None) -> str:
    hostname = _normalize_host(raw_host)
    _reject_private_or_local_host(hostname)

    normalized_allowlist = _ALLOWED_HTTPS_HOSTS if allowed_hosts is None else {_normalize_host(item) for item in allowed_hosts}
    if hostname not in normalized_allowlist:
        raise ValueError(f"URL host is not in allowlist: {hostname}")
    return hostname


def _validate_https_path_prefix(path: str, raw_path: str) -> None:
    if not path.startswith("/") or path.startswith("//"):
        raise ValueError(f"HTTPS path must start with a single '/': {raw_path!r}")
    if "://" in path:
        raise ValueError(f"HTTPS path must not include a URL scheme: {raw_path!r}")


def _has_control_characters(value: str) -> bool:
    return any(ord(ch) < 0x20 for ch in value)


def _validate_https_path_chars(path: str, raw_path: str) -> None:
    if any(ch.isspace() for ch in path):
        raise ValueError(f"HTTPS path must not include whitespace: {raw_path!r}")
    if _has_control_characters(path):
        raise ValueError(f"HTTPS path must not include control characters: {raw_path!r}")


def _validate_https_path_components(path: str, raw_path: str) -> None:
    parsed = urlparse(path)
    if parsed.scheme or parsed.netloc:
        raise ValueError(f"HTTPS path must not include host data: {raw_path!r}")


def require_https_path(raw_path: str) -> str:
    path = (raw_path or "").strip()
    _validate_https_path_prefix(path, raw_path)
    _validate_https_path_chars(path, raw_path)
    _validate_https_path_components(path, raw_path)
    return path


def require_repo_slug(raw: str) -> Tuple[str, str]:
    value = (raw or "").strip()
    if value.count("/") != 1:
        raise ValueError(f"Invalid repository slug: {raw!r}")
    owner, repo = value.split("/", 1)
    return require_repo_segment(owner, label="repository owner"), require_repo_segment(repo, label="repository name")


def require_repo_segment(raw: str, *, label: str) -> str:
    return _require_identifier(raw, label=label, allowed_chars=_SAFE_REPO_SEGMENT_CHARS, min_len=1, max_len=100)


def require_slug(raw: str, *, label: str) -> str:
    return _require_identifier(raw, label=label, allowed_chars=_SAFE_SLUG_CHARS, min_len=1, max_len=120)


def require_sha(raw: str) -> str:
    value = (raw or "").strip()
    if len(value) < 7 or len(value) > 40 or any(ch not in _HEX_CHARS for ch in value):
        raise ValueError(f"Invalid commit SHA: {raw!r}")
    return value


def quote_segment(value: str) -> str:
    return quote(value, safe="")


def quote_path_segment(value: str, *, label: str) -> str:
    checked = _require_identifier(
        value,
        label=label,
        allowed_chars=_SAFE_PATH_SEGMENT_CHARS,
        min_len=1,
        max_len=120,
    )
    return quote(checked, safe="")


def fixed_output_paths(out_dir: str, json_name: str, md_name: str) -> Tuple[Path, Path]:
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
    out_dir, json_name, md_name = _QUALITY_ARTIFACT_LAYOUT[artifact]
    return fixed_output_paths(out_dir, json_name, md_name)


def build_https_request_target(
    *,
    host: HTTPSHost,
    path: str,
) -> HTTPSRequestTarget:
    safe_host = require_allowed_https_host(host.value)
    safe_path = require_https_path(path)
    return HTTPSRequestTarget(host=safe_host, path=safe_path)


def _https_connection() -> Any:
    https_connection_factory = getattr(http.client, "HTTPSConnection", None)
    if https_connection_factory is None:
        raise RuntimeError("HTTPSConnection is unavailable in this Python runtime")
    return https_connection_factory


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
    safe_host = require_allowed_https_host(target.host, allowed_hosts=allowed_hosts)
    safe_path = require_https_path(target.path)

    payload = None
    final_headers = {"Accept": _JSON_CONTENT_TYPE}
    if headers:
        final_headers.update(headers)
    if body is not None:
        payload = json.dumps(body).encode("utf-8")
        final_headers.setdefault("Content-Type", _JSON_CONTENT_TYPE)

    conn = _https_connection()(safe_host, timeout=timeout)  # nosemgrep: validated allowlist host and path
    try:
        conn.request(method, safe_path, body=payload, headers=final_headers)
        response = conn.getresponse()
        raw = response.read().decode("utf-8", errors="replace")
    finally:
        conn.close()

    if response.status >= 400:
        raise HTTPSRequestError(response.status, str(response.reason), raw)

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON response body from {safe_host}{safe_path}") from exc
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
    safe_host = require_allowed_https_host(target.host, allowed_hosts=allowed_hosts)
    safe_path = require_https_path(target.path)

    final_headers = {"Accept": _JSON_CONTENT_TYPE}
    if headers:
        final_headers.update(headers)

    conn = _https_connection()(safe_host, timeout=timeout)  # nosemgrep: validated allowlist host and path
    try:
        conn.request(method, safe_path, headers=final_headers)
        response = conn.getresponse()
        raw = response.read().decode("utf-8", errors="replace")
        response_headers = {k.lower(): v for k, v in response.getheaders()}
    finally:
        conn.close()

    if response.status >= 400:
        raise HTTPSRequestError(response.status, str(response.reason), raw)

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON response body from {safe_host}{safe_path}") from exc
    if not isinstance(parsed, list):
        raise RuntimeError("Expected JSON list response")

    return parsed, response_headers
