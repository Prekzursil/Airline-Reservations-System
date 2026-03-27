from __future__ import absolute_import, division

import io
from email.message import Message
from typing import Any, Dict
import urllib.error

import pytest

from scripts import security_helpers as sec


def _ensure(condition: bool, message: str | None = None) -> None:
    if not condition:
        raise AssertionError(message or "Expected condition to be true.")


def test_identifier_slug_and_sha_helpers() -> None:
    _ensure(sec.require_repo_segment("owner.repo-1", label="owner") == "owner.repo-1")
    _ensure(sec.require_repo_slug("Prekzursil/Airline-Reservations-System") == ("Prekzursil", "Airline-Reservations-System"))
    _ensure(sec.require_slug("feature-1", label="branch") == "feature-1")
    _ensure(sec.require_sha("a1b2c3d") == "a1b2c3d")

    with pytest.raises(ValueError):
        sec.require_repo_slug("invalid-slug")
    with pytest.raises(ValueError):
        sec.require_sha("not-a-sha")


def test_https_url_and_path_helpers() -> None:
    _ensure(
        sec.normalize_https_url(
            "https://api.codacy.com/api/v3/resource?limit=1&query=x",
            allowed_host_suffixes={"codacy.com"},
        )
        == "https://api.codacy.com/api/v3/resource?limit=1&query=x"
    )
    _ensure(
        sec.normalize_https_url(
            "https://api.codacy.com/api/v3/resource?limit=1&query=x",
            allowed_host_suffixes={"codacy.com"},
            strip_query=True,
        )
        == "https://api.codacy.com/api/v3/resource"
    )
    _ensure(sec.require_allowed_https_host("SENTRY.IO.") == "sentry.io")
    _ensure(sec.require_https_path("/repos/owner/repo/commits/a1b2c3d/status") == "/repos/owner/repo/commits/a1b2c3d/status")

    with pytest.raises(ValueError):
        sec.normalize_https_url("http://api.codacy.com/api/v3/resource")
    with pytest.raises(ValueError):
        sec.require_allowed_https_host("localhost")
    with pytest.raises(ValueError):
        sec.require_https_path("repos/owner/repo")


def test_fixed_output_paths_and_quality_artifact_paths_stay_in_workspace(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    out_json, out_md = sec.fixed_output_paths("reports/out", "payload.json", "payload.md")
    _ensure(out_json == (tmp_path / "reports" / "out" / "payload.json").resolve(strict=False))
    _ensure(out_md == (tmp_path / "reports" / "out" / "payload.md").resolve(strict=False))

    qa_json, qa_md = sec.quality_artifact_paths(sec.QualityArtifact.CODACY_ZERO)
    _ensure(qa_json.parent.name == "codacy-zero")
    _ensure(qa_md.name == "codacy.md")

    with pytest.raises(ValueError):
        sec.fixed_output_paths("../outside", "payload.json", "payload.md")


def test_build_https_request_target_and_header_helpers() -> None:
    target = sec.build_https_request_target(
        host=sec.HTTPSHost.GITHUB_API,
        path="/repos/owner/repo/commits/a1b2c3d/status",
    )
    _ensure(target.host == "api.github.com")
    _ensure(target.path == "/repos/owner/repo/commits/a1b2c3d/status")
    _ensure(sec.quote_segment("Owner-1") == "Owner-1")
    _ensure(sec.quote_path_segment("Repo-1", label="repo") == "Repo-1")
    _ensure(sec._normalized_http_method(" patch ") == "PATCH")
    _ensure(sec._safe_timeout_seconds(30) == 30)

    merged = sec._merge_safe_headers({"X-Test": "ok"}, include_json_content_type=False)
    _ensure(merged["Accept"] == "application/json")
    _ensure(merged["X-Test"] == "ok")

    with pytest.raises(ValueError):
        sec._normalized_http_method("TRACE")
    with pytest.raises(ValueError):
        sec._safe_timeout_seconds(0)
    with pytest.raises(ValueError):
        sec._merge_safe_headers({"Bad Header": "x"}, include_json_content_type=False)


def test_request_json_https_success_and_error_paths(monkeypatch) -> None:
    recorded: Dict[str, Any] = {}

    class _Response:
        status = 200
        reason = "OK"

        @staticmethod
        def read():
            return b'{"ok":true}'

        @staticmethod
        def getheaders():
            return [("X-Hits", "1")]

    class _Conn:
        def __init__(self, host: str, timeout: int):
            recorded["host"] = host
            recorded["timeout"] = timeout

        def request(self, method: str, path: str, body=None, headers=None):
            recorded["method"] = method
            recorded["path"] = path
            recorded["body"] = body.decode("utf-8") if body is not None else None
            recorded["headers"] = headers

        @staticmethod
        def getresponse():
            return _Response()

        @staticmethod
        def close():
            recorded["closed"] = True

    monkeypatch.setattr(sec, "_https_connection", lambda: _Conn)

    payload = sec.request_json_https(
        host="api.codacy.com",
        path="/api/v3/issues/search",
        method="POST",
        headers={"Accept": "application/json"},
        body={"x": 1},
    )

    _ensure(payload == {"ok": True})
    _ensure(recorded["host"] == "api.codacy.com")
    _ensure(recorded["path"] == "/api/v3/issues/search")
    _ensure(recorded["method"] == "POST")
    _ensure(recorded["body"] == '{"x": 1}')
    _ensure(recorded["closed"] is True)

    class _ErrorResponse:
        status = 403
        reason = "Forbidden"

        @staticmethod
        def read():
            return b'{"error":"denied"}'

        @staticmethod
        def getheaders():
            return []

    class _ErrorConn(_Conn):
        @staticmethod
        def getresponse():
            return _ErrorResponse()

    monkeypatch.setattr(sec, "_https_connection", lambda: _ErrorConn)

    with pytest.raises(sec.HTTPSRequestError, match="403 Forbidden"):
        sec.request_json_https(host="sentry.io", path="/api/0/projects/org/proj/issues/")


def test_request_json_list_https_target_and_invalid_json(monkeypatch) -> None:
    target = sec.HTTPSRequestTarget(host="api.github.com", path="/repos/owner/repo/commits/a1b2c3d/check-runs")

    response = sec.HTTPSResponsePayload(
        host=target.host,
        path=target.path,
        status=200,
        reason="OK",
        body='[{"name":"verify"}]',
        headers={"x-test": "1"},
    )
    monkeypatch.setattr(sec, "_request_https_payload", lambda **_kwargs: response)

    payload, headers = sec.request_json_list_https_target(target=target)
    _ensure(payload == [{"name": "verify"}])
    _ensure(headers == {"x-test": "1"})

    bad_response = sec.HTTPSResponsePayload(
        host=target.host,
        path=target.path,
        status=200,
        reason="OK",
        body='{"not":"a-list"}',
        headers={},
    )
    monkeypatch.setattr(sec, "_request_https_payload", lambda **_kwargs: bad_response)

    with pytest.raises(RuntimeError, match="Expected JSON list response"):
        sec.request_json_list_https_target(target=target)
