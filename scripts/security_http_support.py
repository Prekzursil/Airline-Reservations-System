from __future__ import absolute_import, annotations, division

import http.client
import json
from typing import Any, Dict, List, Optional

from scripts.security_helpers import (
    HTTPSRequestError,
    HTTPSRequestOptions,
    HTTPSRequestTarget,
    HTTPSResponsePayload,
    _JSON_CONTENT_TYPE,
    _SAFE_HEADER_NAME_CHARS,
)
from scripts.security_validation_support import require_allowed_https_host, require_https_path


def _https_connection() -> Any:
    return http.client.HTTPSConnection


def _normalized_http_method(method: str) -> str:
    value = (method or "").strip().upper()
    if value not in {"DELETE", "GET", "PATCH", "POST", "PUT"}:
        raise ValueError(f"Unsupported HTTP method: {method!r}")
    return value


def _safe_timeout_seconds(timeout: int) -> int:
    try:
        checked = int(timeout)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid timeout: {timeout!r}") from exc
    if checked < 1 or checked > 300:
        raise ValueError(f"Timeout must be between 1 and 300 seconds: {timeout!r}")
    return checked


def _contains_control_characters(value: str) -> bool:
    return any(ord(ch) < 32 for ch in value)


def _validate_header_name(name: str) -> str:
    checked = (name or "").strip()
    if not checked or any(ch not in _SAFE_HEADER_NAME_CHARS for ch in checked):
        raise ValueError(f"Invalid HTTP header name: {name!r}")
    return checked


def _validate_header_value(value: Any, *, name: str) -> str:
    checked = str(value)
    if _contains_control_characters(checked):
        raise ValueError(f"Invalid HTTP header value for {name}: control characters are not allowed")
    return checked


def _merge_safe_headers(headers: Optional[Dict[str, str]], *, include_json_content_type: bool) -> Dict[str, str]:
    final_headers: Dict[str, str] = {"Accept": _JSON_CONTENT_TYPE}
    if headers:
        for name, value in headers.items():
            checked_name = _validate_header_name(name)
            final_headers[checked_name] = _validate_header_value(value, name=checked_name)
    if include_json_content_type:
        final_headers.setdefault("Content-Type", _JSON_CONTENT_TYPE)
    return final_headers


def _request_https_payload(*, target: HTTPSRequestTarget, options: Optional[HTTPSRequestOptions] = None) -> HTTPSResponsePayload:
    resolved_options = options or HTTPSRequestOptions()
    safe_host = require_allowed_https_host(target.host, allowed_hosts=resolved_options.allowed_hosts)
    safe_path = require_https_path(target.path)
    safe_method = _normalized_http_method(resolved_options.method)
    safe_timeout = _safe_timeout_seconds(resolved_options.timeout)

    payload = None
    include_content_type = resolved_options.body is not None
    if resolved_options.body is not None:
        payload = json.dumps(resolved_options.body).encode("utf-8")
    final_headers = _merge_safe_headers(
        resolved_options.headers,
        include_json_content_type=include_content_type,
    )

    conn = _https_connection()(safe_host, timeout=safe_timeout)  # nosemgrep: validated allowlist host and path
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
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON response body from {host}{path}") from exc


def request_json_https(*, host: str, path: str, options: Optional[HTTPSRequestOptions] = None) -> Dict[str, Any]:
    target = HTTPSRequestTarget(
        host=require_allowed_https_host(host, allowed_hosts=(options.allowed_hosts if options else None)),
        path=require_https_path(path),
    )
    return request_json_https_target(target=target, options=options)


def request_json_https_target(*, target: HTTPSRequestTarget, options: Optional[HTTPSRequestOptions] = None) -> Dict[str, Any]:
    response = _request_https_payload(target=target, options=options)
    if response.status >= 400:
        raise HTTPSRequestError(response.status, response.reason, response.body)

    parsed = _parse_json_response(response.body, host=response.host, path=response.path)
    if not isinstance(parsed, dict):
        raise RuntimeError("Expected JSON object response")
    return parsed


def request_json_list_https(*, host: str, path: str, options: Optional[HTTPSRequestOptions] = None) -> tuple[List[Any], Dict[str, str]]:
    target = HTTPSRequestTarget(
        host=require_allowed_https_host(host, allowed_hosts=(options.allowed_hosts if options else None)),
        path=require_https_path(path),
    )
    return request_json_list_https_target(target=target, options=options)


def request_json_list_https_target(
    *,
    target: HTTPSRequestTarget,
    options: Optional[HTTPSRequestOptions] = None,
) -> tuple[List[Any], Dict[str, str]]:
    response = _request_https_payload(target=target, options=options)
    if response.status >= 400:
        raise HTTPSRequestError(response.status, response.reason, response.body)

    parsed = _parse_json_response(response.body, host=response.host, path=response.path)
    if not isinstance(parsed, list):
        raise RuntimeError("Expected JSON list response")
    return parsed, response.headers
