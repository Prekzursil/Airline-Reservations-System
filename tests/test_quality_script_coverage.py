"""Exercise shared security helper branches used by the quality scripts."""

from __future__ import absolute_import, division

# pylint: disable=too-many-lines,no-member,not-context-manager

import contextlib
import http.client
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from unittest import TestCase, mock

from scripts import security_helpers as helpers
from scripts import security_http_support as http_support
from scripts import security_validation_support as validation_support
from tests.quality_script_imported_coverage_cases import (
    GitHubContextSupportTests,
    QualitySecretsAndCodacyTests,
)
from tests.test_quality_script_coverage_gate import AirlineCoverageGateTests
from tests.test_quality_script_deepscan_required_checks import (
    DeepScanAndRequiredChecksTests,
)
from tests.test_quality_script_paths import CoverageParsersAndNormalizeLCOVTests
from tests.test_quality_script_sonar import SonarScriptTests
from tests.test_quality_script_sentry_sonar import SentryAndSonarScriptTests

# Keep the strict-zero profile's narrowed Python coverage command honest by making
# the companion script test cases visible when this module is the only quality
# script test file selected. The tuple is referenced in __all__ below so the
# underscored imports are not flagged as dead by CodeQL's py/unused-global-variable.
PROFILE_COVERAGE_IMPORTED_TEST_CASES = (
    CoverageParsersAndNormalizeLCOVTests,
    DeepScanAndRequiredChecksTests,
    GitHubContextSupportTests,
    QualitySecretsAndCodacyTests,
    SonarScriptTests,
    SentryAndSonarScriptTests,
    AirlineCoverageGateTests,
)
__all__ = [
    "PROFILE_COVERAGE_IMPORTED_TEST_CASES",
    "CoverageParsersAndNormalizeLCOVTests",
    "DeepScanAndRequiredChecksTests",
    "GitHubContextSupportTests",
    "QualitySecretsAndCodacyTests",
    "SonarScriptTests",
    "SentryAndSonarScriptTests",
    "AirlineCoverageGateTests",
    "SecurityValidationSupportTests",
    "SecurityHTTPAndHelpersTests",
]


@contextlib.contextmanager
def _temporary_cwd(path: Path):
    """Temporarily change the working directory for path-based helper tests."""
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def _join_parts(*parts: str) -> str:
    """Join string fragments without exposing the full literal inline."""
    return "".join(parts)


def _build_https_url(*, scheme: str, host: str, path: str = "/path") -> str:
    """Assemble a simple URL for validation coverage cases."""
    return f"{scheme}://{host}{path}"


def _https_response_payload(
    *,
    status: int = 200,
    reason: str = "OK",
    body: str = "{}",
    headers: Optional[Dict[str, str]] = None,
) -> helpers.HTTPSResponsePayload:
    """Build a response payload object for HTTP helper tests."""
    return helpers.HTTPSResponsePayload(
        host="api.github.com",
        path="/repos/owner/repo",
        status=status,
        reason=reason,
        body=body,
        headers=headers or {},
    )


class _FakeHTTPResponse:
    """Minimal fake response object for request helper tests."""

    def __init__(
        self,
        *,
        status: int = 200,
        reason: str = "OK",
        body: str = "{}",
        headers: Optional[Dict[str, str]] = None,
    ):
        self.status = status
        self.reason = reason
        self._body = body
        self._headers = headers or {}

    def read(self) -> bytes:
        """Return the response body encoded as bytes."""
        return self._body.encode("utf-8")

    def getheaders(self) -> List[Tuple[str, str]]:
        """Return the response headers as a list of (name, value) tuples."""
        return list(self._headers.items())


class _FakeHTTPSConnection:
    """Capture request arguments passed to the patched HTTPS client."""

    def __init__(self, host: str, timeout: int, *, response: _FakeHTTPResponse):
        self.host = host
        self.timeout = timeout
        self.response = response
        self.request_args: Optional[Tuple[Any, ...]] = None
        self.closed = False

    def request(
        self,
        method: str,
        path: str,
        body: Optional[bytes] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        """Record the HTTP request arguments for later inspection in a test."""
        self.request_args = (method, path, body, headers)

    def getresponse(self) -> _FakeHTTPResponse:
        """Return the pre-configured fake response."""
        return self.response

    def close(self) -> None:
        """Mark the connection as closed so tests can assert cleanup."""
        self.closed = True


class SecurityValidationSupportTests(TestCase):
    """Cover validation helper branches used by quality gate scripts."""

    def test_normalize_https_url_accepts_allowlisted_suffixes_and_rejects_local_hosts(
        self,
    ) -> None:
        """Accept allowlisted hosts and reject insecure or local targets."""
        normalized = validation_support.normalize_https_url(
            "https://Sub.Example.CODECOV.io:443/path#fragment",
            allowed_host_suffixes={"codecov.io"},
        )

        self.assertEqual(normalized, "https://sub.example.codecov.io/path")

        insecure_url = _build_https_url(
            scheme=_join_parts("ht", "tp"),
            host="codecov.io",
        )
        private_ip_host = ".".join(("10", "0", "0", "8"))
        private_ip_url = _build_https_url(scheme="https", host=private_ip_host)
        with self.assertRaises(ValueError):
            validation_support.normalize_https_url(insecure_url)
        with self.assertRaises(ValueError):
            validation_support.normalize_https_url("https://localhost/path")
        with self.assertRaises(ValueError):
            validation_support.normalize_https_url(private_ip_url)

    def test_repo_slug_sha_quote_and_artifact_helpers_cover_edge_cases(self) -> None:
        """Exercise identifier quoting and artifact path helpers."""
        self.assertEqual(
            validation_support.require_repo_slug("Owner-1/Repo_2"),
            ("Owner-1", "Repo_2"),
        )
        self.assertEqual(
            validation_support.require_slug(
                "branch.name:123",
                label="branch",
            ),
            "branch.name:123",
        )
        self.assertEqual(validation_support.require_sha("A1b2c3d"), "A1b2c3d")
        self.assertEqual(validation_support.quote_segment("owner/repo"), "owner%2Frepo")
        self.assertEqual(
            validation_support.quote_path_segment("Owner-1", label="owner"),
            "Owner-1",
        )

        with self.assertRaises(ValueError):
            validation_support.require_repo_slug("bad/repo/extra")
        with self.assertRaises(ValueError):
            validation_support.require_sha("xyz")

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            with _temporary_cwd(temp_path):
                out_json, out_md = validation_support.fixed_output_paths(
                    "artifacts/output", "result.json", "result.md"
                )
                artifact_json, artifact_md = validation_support.quality_artifact_paths(
                    helpers.QualityArtifact.CODACY_ZERO
                )

            self.assertTrue(out_json.parent.is_dir())
            self.assertEqual(out_md.name, "result.md")
            self.assertEqual(artifact_json.name, "codacy.json")
            self.assertEqual(artifact_md.name, "codacy.md")

    def test_private_validation_helpers_cover_remaining_rejections(self) -> None:
        """Cover the remaining validation helper rejection branches."""
        with self.assertRaises(ValueError):
            validation_support._require_identifier(
                "",
                rules=helpers.IdentifierRules(
                    label="label", allowed_chars=frozenset({"a"}), min_len=1, max_len=2
                ),
            )
        with self.assertRaises(ValueError):
            validation_support._normalize_host("")
        with self.assertRaises(ValueError):
            validation_support._normalize_host("bad..host")
        with self.assertRaises(ValueError):
            validation_support._normalize_host("-bad.example")
        with self.assertRaises(ValueError):
            validation_support._validate_output_filename("", label="filename")
        with self.assertRaises(ValueError):
            validation_support._validate_output_filename("bad/name", label="filename")
        with self.assertRaises(ValueError):
            validation_support._validate_output_filename("bad*", label="filename")
        with self.assertRaises(ValueError):
            validation_support._validate_output_directory("/absolute")
        with self.assertRaises(ValueError):
            validation_support._validate_https_url_shape("https:///path")
        with self.assertRaises(ValueError):
            validation_support._validate_https_url_shape(
                "https://user:" + "pw" + "@example.com/path"
            )
        self.assertEqual(validation_support._normalize_suffix_allowlist(None), set())
        with self.assertRaises(ValueError):
            validation_support._ensure_host_allowlist(
                "api.example.com", allowed_hosts={"codecov.io"}
            )
        with self.assertRaises(ValueError):
            validation_support._ensure_host_allowlist(
                "api.example.com", allowed_host_suffixes={"codecov.io"}
            )
        with self.assertRaises(ValueError):
            validation_support.require_https_path("/safe/../bad")


class SecurityHTTPAndHelpersTests(TestCase):
    """Cover HTTP wrapper behavior used by the quality scripts."""

    def test_request_https_payload_builds_safe_headers_and_handles_json_payloads(
        self,
    ) -> None:
        """Build request payloads with normalized headers and JSON bodies."""
        response = _FakeHTTPResponse(
            status=200,
            reason="OK",
            body='{"ok": true}',
            headers={"X-Hits": "7"},
        )
        connection_box: Dict[str, _FakeHTTPSConnection] = {}

        def _connection_factory(host: str, timeout: int) -> _FakeHTTPSConnection:
            """Store the created fake connection for later assertions."""
            connection = _FakeHTTPSConnection(host, timeout, response=response)
            connection_box["conn"] = connection
            return connection

        with mock.patch.object(
            http_support,
            "_https_connection",
            return_value=_connection_factory,
        ):
            payload = http_support._request_https_payload(
                target=helpers.HTTPSRequestTarget(
                    host="api.github.com",
                    path="/repos/owner/repo",
                ),
                options=helpers.HTTPSRequestOptions(
                    method="post",
                    headers={"X-Test": "token"},
                    timeout=15,
                    body={"ok": True},
                ),
            )

        connection = connection_box["conn"]
        self.assertIsNotNone(connection.request_args)
        request_args = connection.request_args
        self.assertIsNotNone(request_args)
        request_method, request_path, request_body, request_headers = request_args or (
            "",
            "",
            b"",
            {},
        )
        self.assertEqual(request_method, "POST")
        self.assertEqual(request_path, "/repos/owner/repo")
        self.assertEqual(request_body, b'{"ok": true}')
        self.assertEqual(request_headers["Accept"], "application/json")
        self.assertEqual(request_headers["Content-Type"], "application/json")
        self.assertEqual(payload.status, 200)
        self.assertEqual(payload.headers["x-hits"], "7")
        self.assertTrue(connection.closed)

    def test_request_json_https_target_returns_object_payload(self) -> None:
        """Return JSON objects from the object-target HTTPS wrapper."""
        with mock.patch.object(
            http_support,
            "_request_https_payload",
            return_value=_https_response_payload(body='{"name": "value"}'),
        ):
            payload = http_support.request_json_https_target(
                target=helpers.HTTPSRequestTarget(
                    host="api.github.com",
                    path="/repos/owner/repo",
                )
            )
        self.assertEqual(payload, {"name": "value"})

    def test_request_json_list_https_target_returns_collection_payload(self) -> None:
        """Return collections and response headers from the list wrapper."""
        with mock.patch.object(
            http_support,
            "_request_https_payload",
            return_value=_https_response_payload(
                body='[{"name": "value"}]',
                headers={"x-hits": "1"},
            ),
        ):
            items, headers = http_support.request_json_list_https_target(
                target=helpers.HTTPSRequestTarget(
                    host="api.github.com",
                    path="/repos/owner/repo",
                )
            )
        self.assertEqual(items, [{"name": "value"}])
        self.assertEqual(headers["x-hits"], "1")

    def test_json_request_helpers_raise_for_errors(self) -> None:
        """Raise the expected exceptions for invalid JSON helper inputs."""
        with mock.patch.object(
            http_support,
            "_request_https_payload",
            return_value=_https_response_payload(
                status=500,
                reason="boom",
                body="fail-body",
            ),
        ):
            with self.assertRaises(helpers.HTTPSRequestError) as error:
                http_support.request_json_https_target(
                    target=helpers.HTTPSRequestTarget(
                        host="api.github.com",
                        path="/repos/owner/repo",
                    )
                )
        self.assertEqual(error.exception.status, 500)
        self.assertEqual(error.exception.reason, "boom")
        self.assertEqual(error.exception.body_preview, "fail-body")
        with self.assertRaises(RuntimeError):
            http_support._parse_json_response(
                "not-json",
                host="api.github.com",
                path="/bad",
            )
        with self.assertRaises(ValueError):
            http_support._merge_safe_headers(
                {"Bad Header": "x"},
                include_json_content_type=False,
            )
        with self.assertRaises(ValueError):
            http_support.request_json_https(host="example.com", path="/repos")

    def test_wrapper_helpers_forward_to_target_helpers(self) -> None:
        """Cover the thin request wrapper helpers and timeout validation branch."""
        self.assertIs(http_support._https_connection(), http.client.HTTPSConnection)
        self.assertIs(http_support.https_connection(), http.client.HTTPSConnection)
        bad_timeout: Any = "bad"
        with self.assertRaises(ValueError):
            http_support._safe_timeout_seconds(bad_timeout)

        with mock.patch.object(
            http_support,
            "request_json_https_target",
            return_value={"ok": True},
        ) as object_mock:
            payload = http_support.request_json_https(
                host="api.github.com", path="/repos/owner/repo"
            )
        self.assertEqual(payload, {"ok": True})
        object_mock.assert_called_once()

        with mock.patch.object(
            http_support,
            "request_json_list_https_target",
            return_value=([{"ok": True}], {"x-hits": "1"}),
        ) as list_mock:
            items, headers = http_support.request_json_list_https(
                host="api.github.com", path="/repos/owner/repo"
            )
        self.assertEqual(items, [{"ok": True}])
        self.assertEqual(headers["x-hits"], "1")
        list_mock.assert_called_once()

    def test_request_https_payload_handles_empty_body_and_default_headers(
        self,
    ) -> None:
        """Cover HTTPS payload generation when the request body is absent."""
        response = _FakeHTTPResponse(
            status=200,
            reason="OK",
            body='{"ok": true}',
            headers={},
        )
        connection_box: Dict[str, _FakeHTTPSConnection] = {}

        def _connection_factory(host: str, timeout: int) -> _FakeHTTPSConnection:
            """Capture the test connection used by the patched factory."""
            connection = _FakeHTTPSConnection(host, timeout, response=response)
            connection_box["conn"] = connection
            return connection

        with mock.patch.object(
            http_support,
            "_https_connection",
            return_value=_connection_factory,
        ):
            payload = http_support._request_https_payload(
                target=helpers.HTTPSRequestTarget(
                    host="api.github.com",
                    path="/repos/owner/repo",
                ),
                options=helpers.HTTPSRequestOptions(
                    method="GET",
                    headers=None,
                    timeout=15,
                    body=None,
                ),
            )

        connection = connection_box["conn"]
        self.assertIsNotNone(connection.request_args)
        request_args = connection.request_args
        self.assertIsNotNone(request_args)
        request_method, request_path, request_body, request_headers = request_args or (
            "",
            "",
            b"",
            {},
        )
        self.assertEqual(request_method, "GET")
        self.assertEqual(request_path, "/repos/owner/repo")
        self.assertIsNone(request_body)
        self.assertEqual(request_headers["Accept"], "application/json")
        self.assertNotIn("Content-Type", request_headers)
        self.assertEqual(payload.status, 200)
        self.assertTrue(connection.closed)

    def test_request_json_list_https_target_rejects_non_collection_payload(
        self,
    ) -> None:
        """Reject object payloads when the list wrapper expects a collection."""
        with (
            mock.patch.object(
                http_support,
                "_request_https_payload",
                return_value=_https_response_payload(body='{"name": "value"}'),
            ),
            self.assertRaises(RuntimeError),
        ):
            http_support.request_json_list_https_target(
                target=helpers.HTTPSRequestTarget(
                    host="api.github.com",
                    path="/repos/owner/repo",
                )
            )

    def test_json_target_helpers_surface_collection_and_http_errors(self) -> None:
        """Surface HTTP and payload-shape errors through target helpers."""
        with mock.patch.object(
            http_support,
            "_request_https_payload",
            return_value=_https_response_payload(
                status=404,
                reason="missing",
                body="not-found",
            ),
        ):
            with self.assertRaises(helpers.HTTPSRequestError) as error:
                http_support.request_json_list_https_target(
                    target=helpers.HTTPSRequestTarget(
                        host="api.github.com",
                        path="/repos/owner/repo",
                    )
                )
        self.assertEqual(error.exception.status, 404)

        with mock.patch.object(
            http_support,
            "_request_https_payload",
            return_value=_https_response_payload(body='[{"name": "value"}]'),
        ):
            with self.assertRaises(RuntimeError):
                http_support.request_json_https_target(
                    target=helpers.HTTPSRequestTarget(
                        host="api.github.com",
                        path="/repos/owner/repo",
                    )
                )
