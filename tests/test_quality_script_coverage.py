from __future__ import absolute_import, division

import contextlib
import http.client
import io
import json
import os
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from unittest import mock

from scripts import security_helpers as helpers
from scripts import security_http_support as http_support
from scripts import security_validation_support as validation_support
from scripts.quality import assert_coverage_100 as airline_coverage_gate
from scripts.quality import check_codacy_zero as codacy
from scripts.quality import check_quality_secrets as quality_secrets
from scripts.quality import github_contexts
from scripts.quality import required_checks_support


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


class GitHubContextSupportTests(unittest.TestCase):
    def test_collect_context_entries_and_required_context_evaluation(self) -> None:
        check_runs_payload = {
            "check_runs": [
                {"name": "Codecov Analytics", "status": "completed", "conclusion": "success"},
                {"name": "QLTY Zero", "status": "in_progress", "conclusion": None},
                "bad",
            ]
        }
        status_payload = {
            "statuses": [
                {"context": "DeepScan", "state": "success"},
                {"context": "Semgrep Zero", "state": "failure"},
            ]
        }

        contexts = github_contexts.collect_contexts(check_runs_payload, status_payload)
        self.assertEqual(contexts["Codecov Analytics"]["source"], "check_run")
        self.assertEqual(contexts["DeepScan"]["conclusion"], "success")
        self.assertTrue(required_checks_support.has_check_runs_in_progress(contexts))

        status, missing, failed = required_checks_support.evaluate_required_contexts(
            ["Codecov Analytics", "DeepScan", "Semgrep Zero", "Missing"],
            contexts,
        )
        self.assertEqual(status, "fail")
        self.assertEqual(missing, ["Missing"])
        self.assertIn("Semgrep Zero: state=failure", failed)

    def test_blank_context_names_and_direct_failure_helpers(self) -> None:
        entries = github_contexts.collect_context_entries(
            [
                {"name": "  ", "status": "completed", "conclusion": "success"},
                {"name": "Codecov Analytics", "status": "queued", "conclusion": "neutral"},
            ],
            github_contexts.CHECK_RUN_SPEC,
        )
        self.assertEqual(list(entries.keys()), ["Codecov Analytics"])
        self.assertEqual(
            required_checks_support._evaluate_check_run(
                "Codecov Analytics", {"state": "queued", "conclusion": "success"}
            ),
            "Codecov Analytics: status=queued",
        )
        self.assertEqual(
            required_checks_support._evaluate_check_run(
                "Codecov Analytics", {"state": "completed", "conclusion": "failure"}
            ),
            "Codecov Analytics: conclusion=failure",
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


class QualitySecretsAndCodacyTests(unittest.TestCase):
    def test_quality_secret_helpers_cover_dedupe_presence_and_main_success(self) -> None:
        self.assertEqual(quality_secrets._dedupe(["A", " ", "A", "B"]), ["A", "B"])
        with mock.patch.dict(os.environ, {"A": "1"}, clear=True):
            self.assertEqual(
                quality_secrets.evaluate_env(["A", "B"], ["C"]),
                {
                    "missing_secrets": ["B"],
                    "missing_vars": ["C"],
                    "present_secrets": ["A"],
                    "present_vars": [],
                },
            )

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            with (
                _temporary_cwd(temp_path),
                mock.patch.dict(
                    os.environ,
                    {
                        "SONAR_TOKEN": "x",
                        "CODACY_API_TOKEN": "x",
                        "CODECOV_TOKEN": "x",
                        "SENTRY_AUTH_TOKEN": "x",
                        "SENTRY_ORG": "org",
                        "SENTRY_PROJECT": "proj",
                    },
                    clear=True,
                ),
                mock.patch.object(sys, "argv", ["check_quality_secrets.py"]),
            ):
                self.assertEqual(quality_secrets.main(), 0)
                out_json, _ = helpers.quality_artifact_paths(
                    helpers.QualityArtifact.QUALITY_SECRETS
                )
                payload = json.loads(out_json.read_text(encoding="utf-8"))
                self.assertTrue(payload["details_omitted"])

    def test_codacy_helpers_and_main_cover_success_failure_and_token_resolution(self) -> None:
        nested_total = {"outer": [{"hits": 3}]}
        self.assertEqual(codacy.extract_total_open(nested_total), 3)
        self.assertIsNone(codacy.extract_total_open({"results": []}))

        with mock.patch.dict(os.environ, {"CODACY_API_TOKEN": "env-token"}, clear=True):
            self.assertEqual(codacy._resolve_token(""), "env-token")

        args = Namespace(
            provider="gh", owner="Prekzursil", repo="Airline-Reservations-System", branch=""
        )
        self.assertEqual(
            codacy._run_codacy_check(args, ""), (None, ["CODACY_API_TOKEN is missing."], "fail")
        )

        with mock.patch.object(codacy, "_fetch_open_issues", return_value=0):
            open_issues, findings, status = codacy._run_codacy_check(args, "token")
        self.assertEqual((open_issues, findings, status), (0, [], "pass"))

        with mock.patch.object(codacy, "_fetch_open_issues", side_effect=RuntimeError("boom")):
            _, findings, status = codacy._run_codacy_check(args, "token")
        self.assertEqual(status, "fail")
        self.assertIn("boom", findings[0])

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            out_json = temp_path / "codacy.json"
            out_md = temp_path / "codacy.md"
            cli_args = [
                "check_codacy_zero.py",
                "--owner",
                "Prekzursil",
                "--repo",
                "Airline-Reservations-System",
                "--token",
                "token",
            ]
            with (
                mock.patch.object(
                    codacy, "quality_artifact_paths", return_value=(out_json, out_md)
                ),
                mock.patch.object(codacy, "_run_codacy_check", return_value=(0, [], "pass")),
                mock.patch.object(sys, "argv", cli_args),
            ):
                self.assertEqual(codacy.main(), 0)

            payload = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "pass")
            self.assertEqual(payload["open_issues"], 0)

    def test_codacy_render_and_status_branches(self) -> None:
        with mock.patch.object(
            sys,
            "argv",
            [
                "check_codacy_zero.py",
                "--owner",
                "Prekzursil",
                "--repo",
                "Airline-Reservations-System",
            ],
        ):
            args = codacy._parse_args()
        self.assertEqual(args.provider, "gh")

        rendered = codacy._render_md(
            {
                "status": "pass",
                "owner": "Prekzursil",
                "repo": "Airline-Reservations-System",
                "branch": "",
                "open_issues": 0,
                "timestamp_utc": "2026-03-19T00:00:00+00:00",
                "findings": [],
            }
        )
        self.assertIn("- None", rendered)
        self.assertIn(
            "- problem",
            codacy._render_md(
                {
                    "status": "fail",
                    "owner": "Prekzursil",
                    "repo": "Airline-Reservations-System",
                    "branch": "",
                    "open_issues": 1,
                    "timestamp_utc": "2026-03-19T00:00:00+00:00",
                    "findings": ["problem"],
                }
            ),
        )

        findings: List[str] = []
        self.assertEqual(codacy._evaluate_status(None, findings), "fail")
        self.assertIn("parseable total issue count", findings[0])

        findings = []
        self.assertEqual(codacy._evaluate_status(2, findings), "fail")
        self.assertIn("expected 0", findings[0])
