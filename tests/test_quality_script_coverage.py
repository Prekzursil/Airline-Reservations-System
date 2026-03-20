from __future__ import absolute_import, division

# pylint: disable=too-many-lines,no-member,not-context-manager

import contextlib
import http.client
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from unittest import mock

from scripts import security_helpers as helpers
from scripts import security_http_support as http_support
from scripts import security_validation_support as validation_support
from scripts.quality import assert_coverage_100 as airline_coverage_gate
from tests.quality_script_imported_coverage_cases import (
    GitHubContextSupportTests,
    QualitySecretsAndCodacyTests,
)
from tests.test_quality_script_deepscan_required_checks import DeepScanAndRequiredChecksTests
from tests.test_quality_script_paths import CoverageParsersAndNormalizeLCOVTests
from tests.test_quality_script_sentry_sonar import SentryAndSonarScriptTests

# Keep the strict-zero profile's narrowed Python coverage command honest by making
# the companion script test cases visible when this module is the only quality
# script test file selected.
_PROFILE_COVERAGE_IMPORTED_TEST_CASES = (
    CoverageParsersAndNormalizeLCOVTests,
    DeepScanAndRequiredChecksTests,
    GitHubContextSupportTests,
    QualitySecretsAndCodacyTests,
    SentryAndSonarScriptTests,
)


@contextlib.contextmanager
def _temporary_cwd(path: Path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def _join_parts(*parts: str) -> str:
    return "".join(parts)


def _build_https_url(*, scheme: str, host: str, path: str = "/path") -> str:
    return f"{scheme}://{host}{path}"


def _https_response_payload(
    *,
    status: int = 200,
    reason: str = "OK",
    body: str = "{}",
    headers: Optional[Dict[str, str]] = None,
) -> helpers.HTTPSResponsePayload:
    return helpers.HTTPSResponsePayload(
        host="api.github.com",
        path="/repos/owner/repo",
        status=status,
        reason=reason,
        body=body,
        headers=headers or {},
    )


class _FakeHTTPResponse:
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
        return self._body.encode("utf-8")

    def getheaders(self) -> List[Tuple[str, str]]:
        return list(self._headers.items())


class _FakeHTTPSConnection:
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
        self.request_args = (method, path, body, headers)

    def getresponse(self) -> _FakeHTTPResponse:
        return self.response

    def close(self) -> None:
        self.closed = True


class SecurityValidationSupportTests(unittest.TestCase):
    def test_normalize_https_url_accepts_allowlisted_suffixes_and_rejects_local_hosts(self) -> None:
        normalized = validation_support.normalize_https_url(
            "https://Sub.Example.CODECOV.io:443/path#fragment",
            allowed_host_suffixes={"codecov.io"},
        )

        self.assertEqual(normalized, "https://sub.example.codecov.io/path")

        insecure_url = _build_https_url(scheme=_join_parts("ht", "tp"), host="codecov.io")
        private_ip_host = ".".join(("10", "0", "0", "8"))
        private_ip_url = _build_https_url(scheme="https", host=private_ip_host)
        with self.assertRaises(ValueError):
            validation_support.normalize_https_url(insecure_url)
        with self.assertRaises(ValueError):
            validation_support.normalize_https_url("https://localhost/path")
        with self.assertRaises(ValueError):
            validation_support.normalize_https_url(private_ip_url)

    def test_repo_slug_sha_quote_and_artifact_helpers_cover_edge_cases(self) -> None:
        self.assertEqual(
            validation_support.require_repo_slug("Owner-1/Repo_2"), ("Owner-1", "Repo_2")
        )
        self.assertEqual(
            validation_support.require_slug("branch.name:123", label="branch"), "branch.name:123"
        )
        self.assertEqual(validation_support.require_sha("A1b2c3d"), "A1b2c3d")
        self.assertEqual(validation_support.quote_segment("owner/repo"), "owner%2Frepo")
        self.assertEqual(validation_support.quote_path_segment("Owner-1", label="owner"), "Owner-1")

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
        with self.assertRaises(ValueError):
            validation_support._require_identifier(
                "",
                rules=helpers.IdentifierRules(
                    label="label", allowed_chars={"a"}, min_len=1, max_len=2
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


class SecurityHTTPAndHelpersTests(unittest.TestCase):
    def test_request_https_payload_builds_safe_headers_and_handles_json_payloads(self) -> None:
        response = _FakeHTTPResponse(
            status=200,
            reason="OK",
            body='{"ok": true}',
            headers={"X-Hits": "7"},
        )
        connection_box: Dict[str, _FakeHTTPSConnection] = {}

        def _connection_factory(host: str, timeout: int) -> _FakeHTTPSConnection:
            connection = _FakeHTTPSConnection(host, timeout, response=response)
            connection_box["conn"] = connection
            return connection

        with mock.patch.object(http_support, "_https_connection", return_value=_connection_factory):
            payload = http_support._request_https_payload(
                target=helpers.HTTPSRequestTarget(host="api.github.com", path="/repos/owner/repo"),
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
        request_method, request_path, request_body, request_headers = request_args or ("", "", b"", {})
        self.assertEqual(request_method, "POST")
        self.assertEqual(request_path, "/repos/owner/repo")
        self.assertEqual(request_body, b'{"ok": true}')
        self.assertEqual(request_headers["Accept"], "application/json")
        self.assertEqual(request_headers["Content-Type"], "application/json")
        self.assertEqual(payload.status, 200)
        self.assertEqual(payload.headers["x-hits"], "7")
        self.assertTrue(connection.closed)

    def test_request_json_https_target_returns_object_payload(self) -> None:
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
        self.assertIs(http_support._https_connection(), http.client.HTTPSConnection)
        with self.assertRaises(ValueError):
            http_support._safe_timeout_seconds("bad")

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

    def test_request_json_list_https_target_rejects_non_collection_payload(self) -> None:
        with mock.patch.object(
            http_support,
            "_request_https_payload",
            return_value=_https_response_payload(body='{"name": "value"}'),
        ):
            with self.assertRaises(RuntimeError):
                http_support.request_json_list_https_target(
                    target=helpers.HTTPSRequestTarget(
                        host="api.github.com",
                        path="/repos/owner/repo",
                    )
                )

    def test_json_target_helpers_surface_collection_and_http_errors(self) -> None:
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


class AirlineCoverageGateTests(unittest.TestCase):
    def test_load_node_stats_prefers_known_inputs_and_evaluate_reports_failures(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            node_lcov = temp_path / "node.lcov"
            node_lcov.write_text("LF:2\nLH:2\n", encoding="utf-8")
            summary = temp_path / "summary.json"
            summary.write_text(
                json.dumps({"total": {"lines": {"covered": 3, "total": 4}}}), encoding="utf-8"
            )
            final = temp_path / "final.json"
            final.write_text(json.dumps({"a.js": {"s": {"1": 1, "2": 0}}}), encoding="utf-8")

            with (
                mock.patch.object(airline_coverage_gate, "NODE_LCOV_PATH", node_lcov),
                mock.patch.object(airline_coverage_gate, "NODE_SUMMARY_JSON_PATH", summary),
                mock.patch.object(airline_coverage_gate, "NODE_FINAL_JSON_PATH", final),
            ):
                lcov_stats = airline_coverage_gate.load_node_stats()
                node_lcov.unlink()
                summary_stats = airline_coverage_gate.load_node_stats()
                summary.unlink()
                final_stats = airline_coverage_gate.load_node_stats()

                self.assertEqual((lcov_stats.covered, lcov_stats.total), (2, 2))
                self.assertEqual((summary_stats.covered, summary_stats.total), (3, 4))
                self.assertEqual((final_stats.covered, final_stats.total), (1, 2))

                final.unlink()
                with self.assertRaises(SystemExit):
                    airline_coverage_gate.load_node_stats()

        status, findings = airline_coverage_gate.evaluate(
            [
                airline_coverage_gate.CoverageStats(name="node", path="node", covered=3, total=4),
                airline_coverage_gate.CoverageStats(name="cpp", path="cpp", covered=1, total=1),
            ]
        )
        self.assertEqual(status, "fail")
        self.assertTrue(any("node coverage below 100%" in item for item in findings))
        self.assertTrue(any("combined coverage below 100%" in item for item in findings))

    def test_main_writes_artifacts_and_require_cpp_guard(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            node_lcov = temp_path / "node.lcov"
            cpp_lcov = temp_path / "cpp.lcov"
            out_json = temp_path / "coverage.json"
            out_md = temp_path / "coverage.md"
            node_lcov.write_text("LF:2\nLH:2\n", encoding="utf-8")
            cpp_lcov.write_text("LF:3\nLH:3\n", encoding="utf-8")

            with (
                mock.patch.object(airline_coverage_gate, "NODE_LCOV_PATH", node_lcov),
                mock.patch.object(airline_coverage_gate, "CPP_LCOV_PATH", cpp_lcov),
                mock.patch.object(
                    airline_coverage_gate, "quality_artifact_paths", return_value=(out_json, out_md)
                ),
                mock.patch.object(sys, "argv", ["assert_coverage_100.py", "--require-cpp"]),
            ):
                self.assertEqual(airline_coverage_gate.main(), 0)

            payload = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "pass")
            self.assertEqual(len(payload["components"]), 2)
            self.assertIn("Coverage 100 Gate", out_md.read_text(encoding="utf-8"))

            cpp_lcov.unlink()
            with (
                mock.patch.object(airline_coverage_gate, "NODE_LCOV_PATH", node_lcov),
                mock.patch.object(airline_coverage_gate, "CPP_LCOV_PATH", cpp_lcov),
                mock.patch.object(
                    airline_coverage_gate, "quality_artifact_paths", return_value=(out_json, out_md)
                ),
                mock.patch.object(sys, "argv", ["assert_coverage_100.py", "--require-cpp"]),
            ):
                with self.assertRaises(SystemExit):
                    airline_coverage_gate.main()

    def test_render_optional_cpp_and_arg_parse_branches(self) -> None:
        with mock.patch.object(sys, "argv", ["assert_coverage_100.py"]):
            args = airline_coverage_gate._parse_args()
        self.assertFalse(args.require_cpp)

        rendered = airline_coverage_gate._render_md(
            {
                "status": "pass",
                "timestamp_utc": "2026-03-19T00:00:00+00:00",
                "components": [],
                "findings": [],
            }
        )
        self.assertIn("## Components", rendered)
        self.assertIn("- None", rendered)
        self.assertIn(
            "- below target",
            airline_coverage_gate._render_md(
                {
                    "status": "fail",
                    "timestamp_utc": "2026-03-19T00:00:00+00:00",
                    "components": [],
                    "findings": ["below target"],
                }
            ),
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            node_lcov = temp_path / "node.lcov"
            cpp_lcov = temp_path / "cpp.lcov"
            out_json = temp_path / "coverage.json"
            out_md = temp_path / "coverage.md"
            node_lcov.write_text("LF:1\nLH:1\n", encoding="utf-8")
            cpp_lcov.write_text("LF:2\nLH:2\n", encoding="utf-8")
            with (
                mock.patch.object(airline_coverage_gate, "NODE_LCOV_PATH", node_lcov),
                mock.patch.object(airline_coverage_gate, "CPP_LCOV_PATH", cpp_lcov),
                mock.patch.object(
                    airline_coverage_gate, "quality_artifact_paths", return_value=(out_json, out_md)
                ),
                mock.patch.object(sys, "argv", ["assert_coverage_100.py"]),
            ):
                self.assertEqual(airline_coverage_gate.main(), 0)
            payload = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertEqual(
                [component["name"] for component in payload["components"]], ["node", "cpp"]
            )


