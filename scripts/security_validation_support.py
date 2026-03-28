from __future__ import absolute_import, annotations, division

import ipaddress
from pathlib import Path
from typing import Any, FrozenSet, List, Optional, Set, Tuple
from urllib.parse import quote, urlparse, urlunparse

from scripts.security_helpers import (
    HTTPSRequestTarget,
    HTTPSHost,
    IdentifierRules,
    QualityArtifact,
    _ALLOWED_HTTPS_HOSTS,
    _HEX_CHARS,
    _HOST_CHARS,
    _QUALITY_ARTIFACT_LAYOUT,
    _SAFE_OUTPUT_NAME_CHARS,
    _SAFE_PATH_SEGMENT_CHARS,
    _SAFE_REPO_SEGMENT_CHARS,
    _SAFE_SLUG_CHARS,
)


def _require_identifier(raw: str, *, rules: IdentifierRules) -> str:
    value = (raw or "").strip()
    if len(value) < rules.min_len or len(value) > rules.max_len:
        raise ValueError(f"Invalid {rules.label}: {raw!r}")
    if any(ch not in rules.allowed_chars for ch in value):
        raise ValueError(f"Invalid {rules.label}: {raw!r}")
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
    if _has_invalid_host_characters(host) or ".." in host:
        raise ValueError(f"Invalid HTTPS host: {raw_host!r}")
    labels = host.split(".")
    if _has_empty_host_label(labels) or _has_invalid_hyphen_label(labels):
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
    if not raw or raw.startswith("/"):
        raise ValueError(f"Invalid output directory: {out_dir!r}")

    parts: List[str] = []
    for segment in raw.split("/"):
        if segment:
            parts.append(_validate_output_filename(segment, label="output directory segment"))
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
    return any(hostname == suffix or hostname.endswith(f".{suffix}") for suffix in suffixes)


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
            getattr(ip_value, "is_unspecified", False),
        )
    )


def _reject_private_or_local_host(hostname: str) -> None:
    ip_value = _parse_ip_or_none(hostname)
    if ip_value is not None and _is_private_or_local_address(ip_value):
        raise ValueError(f"URL host must not be a private or local address: {hostname}")
    if hostname in {"localhost", "localhost.localdomain"} or hostname.endswith(".localhost"):
        raise ValueError(f"URL host must not be local: {hostname}")


def normalize_https_url(
    raw_url: str,
    *,
    allowed_hosts: Optional[Set[str]] = None,
    allowed_host_suffixes: Optional[Set[str]] = None,
) -> str:
    parsed, hostname = _validate_https_url_shape(raw_url)
    _reject_private_or_local_host(hostname)
    _ensure_host_allowlist(
        hostname,
        allowed_hosts=allowed_hosts,
        allowed_host_suffixes=allowed_host_suffixes,
    )
    normalized = parsed._replace(
        scheme="https",
        netloc=hostname if parsed.port in {None, 443} else f"{hostname}:{parsed.port}",
        params="",
        fragment="",
    )
    return urlunparse(normalized)


def require_allowed_https_host(host: str, *, allowed_hosts: Optional[Set[str]] = None) -> str:
    checked = _normalize_host(host)
    _reject_private_or_local_host(checked)
    allowed = _ALLOWED_HTTPS_HOSTS if allowed_hosts is None else set(allowed_hosts)
    if checked not in _normalize_host_set(set(allowed)):
        raise ValueError(f"HTTPS host is not allowlisted: {host!r}")
    return checked


def _validate_https_path_prefix(path: str, raw_path: str) -> None:
    if not path.startswith("/") or path.startswith("//"):
        raise ValueError(f"HTTPS path must start with a single '/': {raw_path!r}")


def _has_control_characters(path: str) -> bool:
    return any(ord(ch) < 32 for ch in path)


def _validate_https_path_chars(path: str, raw_path: str) -> None:
    if _has_control_characters(path):
        raise ValueError(f"HTTPS path contains control characters: {raw_path!r}")


def _validate_https_path_components(path: str, raw_path: str) -> None:
    if "/../" in f"{path}/" or "/./" in f"{path}/":
        raise ValueError(f"HTTPS path must not contain relative traversal: {raw_path!r}")


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
    return _require_identifier(
        raw,
        rules=IdentifierRules(label=label, allowed_chars=_SAFE_REPO_SEGMENT_CHARS, min_len=1, max_len=100),
    )


def require_slug(raw: str, *, label: str) -> str:
    return _require_identifier(
        raw,
        rules=IdentifierRules(label=label, allowed_chars=_SAFE_SLUG_CHARS, min_len=1, max_len=120),
    )


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
        rules=IdentifierRules(label=label, allowed_chars=_SAFE_PATH_SEGMENT_CHARS, min_len=1, max_len=120),
    )
    return quote(checked, safe="")


def fixed_output_paths(out_dir: str, json_name: str, md_name: str) -> Tuple[Path, Path]:
    root = Path.cwd().resolve()
    safe_dir = _validate_output_directory(out_dir)
    safe_json = _validate_output_filename(json_name, label="JSON filename")
    safe_md = _validate_output_filename(md_name, label="Markdown filename")
    final_dir = root / safe_dir
    final_dir.mkdir(parents=True, exist_ok=True)
    return final_dir / safe_json, final_dir / safe_md


def quality_artifact_paths(artifact: QualityArtifact) -> Tuple[Path, Path]:
    out_dir, json_name, md_name = _QUALITY_ARTIFACT_LAYOUT[artifact]
    return fixed_output_paths(out_dir, json_name, md_name)


def build_https_request_target(*, host: HTTPSHost, path: str) -> HTTPSRequestTarget:
    return HTTPSRequestTarget(
        host=require_allowed_https_host(host.value),
        path=require_https_path(path),
    )
