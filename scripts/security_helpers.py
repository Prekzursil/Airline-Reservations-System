from __future__ import absolute_import, annotations, division

import string
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple

_SAFE_REPO_SEGMENT_CHARS: FrozenSet[str] = frozenset(string.ascii_letters + string.digits + '._-')
_SAFE_SLUG_CHARS: FrozenSet[str] = frozenset(string.ascii_letters + string.digits + '._:-')
_SAFE_PATH_SEGMENT_CHARS: FrozenSet[str] = frozenset(string.ascii_letters + string.digits + '._-')
_SAFE_OUTPUT_NAME_CHARS: FrozenSet[str] = frozenset(string.ascii_letters + string.digits + '._-')
_HEX_CHARS: FrozenSet[str] = frozenset(string.hexdigits)
_HOST_CHARS: FrozenSet[str] = frozenset(string.ascii_lowercase + string.digits + '.-')
_JSON_CONTENT_TYPE = 'application/json'
_SAFE_HEADER_NAME_CHARS: FrozenSet[str] = frozenset(string.ascii_letters + string.digits + '-')
_ALLOWED_HTTPS_HOSTS: FrozenSet[str] = frozenset(
    {
        'api.github.com',
        'api.codacy.com',
        'sentry.io',
        'sonarcloud.io',
    }
)


class HTTPSHost(str, Enum):
    GITHUB_API = 'api.github.com'
    CODACY_API = 'api.codacy.com'
    SENTRY = 'sentry.io'
    SONARCLOUD = 'sonarcloud.io'


class QualityArtifact(str, Enum):
    COVERAGE_100 = 'coverage-100'
    CODACY_ZERO = 'codacy-zero'
    DEEPSCAN_ZERO = 'deepscan-zero'
    QUALITY_SECRETS = 'quality-secrets'
    REQUIRED_CHECKS = 'quality-zero-gate'
    SENTRY_ZERO = 'sentry-zero'
    SONAR_ZERO = 'sonar-zero'


@dataclass(frozen=True)
class HTTPSRequestTarget:
    host: str
    path: str


@dataclass(frozen=True)
class IdentifierRules:
    label: str
    allowed_chars: FrozenSet[str]
    min_len: int
    max_len: int


@dataclass(frozen=True)
class HTTPSResponsePayload:
    host: str
    path: str
    status: int
    reason: str
    body: str
    headers: Dict[str, str]


@dataclass(frozen=True)
class HTTPSRequestOptions:
    method: str = 'GET'
    headers: Optional[Dict[str, str]] = None
    timeout: int = 30
    body: Optional[Dict[str, Any]] = None
    allowed_hosts: Optional[Set[str]] = None


_QUALITY_ARTIFACT_LAYOUT: Dict[QualityArtifact, Tuple[str, str, str]] = {
    QualityArtifact.COVERAGE_100: ('coverage-100', 'coverage.json', 'coverage.md'),
    QualityArtifact.CODACY_ZERO: ('codacy-zero', 'codacy.json', 'codacy.md'),
    QualityArtifact.DEEPSCAN_ZERO: ('deepscan-zero', 'deepscan.json', 'deepscan.md'),
    QualityArtifact.QUALITY_SECRETS: ('quality-secrets', 'secrets.json', 'secrets.md'),
    QualityArtifact.REQUIRED_CHECKS: ('quality-zero-gate', 'required-checks.json', 'required-checks.md'),
    QualityArtifact.SENTRY_ZERO: ('sentry-zero', 'sentry.json', 'sentry.md'),
    QualityArtifact.SONAR_ZERO: ('sonar-zero', 'sonar.json', 'sonar.md'),
}


class HTTPSRequestError(RuntimeError):
    """Structured HTTPS request error with status metadata for retry logic."""

    def __init__(self, status: int, reason: str, body: str):
        self.status = status
        self.reason = reason
        self.body_preview = body[:400]
        super().__init__(f'HTTPS request failed: {status} {reason}; body={self.body_preview}')


from scripts.security_validation_support import (
    _ensure_host_allowlist,
    _has_control_characters,
    _has_empty_host_label,
    _has_invalid_host_characters,
    _has_invalid_hyphen_label,
    _is_hostname_allowed_by_suffix,
    _is_private_or_local_address,
    _normalize_host,
    _normalize_host_set,
    _normalize_suffix_allowlist,
    _parse_ip_or_none,
    _reject_private_or_local_host,
    _require_identifier,
    _validate_https_path_chars,
    _validate_https_path_components,
    _validate_https_path_prefix,
    _validate_https_url_shape,
    _validate_output_directory,
    _validate_output_filename,
    build_https_request_target,
    fixed_output_paths,
    normalize_https_url,
    quality_artifact_paths,
    quote_path_segment,
    quote_segment,
    require_allowed_https_host,
    require_https_path,
    require_repo_segment,
    require_repo_slug,
    require_sha,
    require_slug,
)
from scripts.security_http_support import (
    _contains_control_characters,
    _https_connection,
    _merge_safe_headers,
    _normalized_http_method,
    _parse_json_response,
    _request_https_payload,
    _safe_timeout_seconds,
    _validate_header_name,
    _validate_header_value,
    request_json_https,
    request_json_https_target,
    request_json_list_https,
    request_json_list_https_target,
)
