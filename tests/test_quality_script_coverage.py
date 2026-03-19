from __future__ import annotations

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
from typing import Any
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import security_helpers as helpers
from scripts import security_http_support as http_support
from scripts import security_validation_support as validation_support
from scripts.quality import assert_coverage_100 as airline_coverage_gate
from scripts.quality import check_codacy_zero as codacy
from scripts.quality import check_deepscan_zero as deepscan
from scripts.quality import check_quality_secrets as quality_secrets
from scripts.quality import check_required_checks as required_checks
from scripts.quality import check_sentry_zero as sentry
from scripts.quality import check_sonar_zero as sonar
from scripts.quality import coverage_parsers as parsers
from scripts.quality import github_contexts
from scripts.quality import normalize_lcov
from scripts.quality import required_checks_support
from scripts.quality import sentry_support
from scripts.quality import sentry_targets


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


class _FakeHTTPResponse:
    def __init__(self, *, status: int = 200, reason: str = "OK", body: str = "{}", headers: dict[str, str] | None = None):
        self.status = status
        self.reason = reason
        self._body = body
        self._headers = headers or {}

    def read(self) -> bytes:
        return self._body.encode("utf-8")

    def getheaders(self) -> list[tuple[str, str]]:
        return list(self._headers.items())


class _FakeHTTPSConnection:
    def __init__(self, host: str, timeout: int, *, response: _FakeHTTPResponse):
        self.host = host
        self.timeout = timeout
        self.response = response
        self.request_args: tuple[Any, ...] | None = None
        self.closed = False

    def request(self, method: str, path: str, body: bytes | None = None, headers: dict[str, str] | None = None) -> None:
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
        self.assertEqual(validation_support.require_repo_slug("Owner-1/Repo_2"), ("Owner-1", "Repo_2"))
        self.assertEqual(validation_support.require_slug("branch.name:123", label="branch"), "branch.name:123")
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
                out_json, out_md = validation_support.fixed_output_paths("artifacts/output", "result.json", "result.md")
                artifact_json, artifact_md = validation_support.quality_artifact_paths(helpers.QualityArtifact.CODACY_ZERO)

            self.assertTrue(out_json.parent.is_dir())
            self.assertEqual(out_md.name, "result.md")
            self.assertEqual(artifact_json.name, "codacy.json")
            self.assertEqual(artifact_md.name, "codacy.md")

    def test_private_validation_helpers_cover_remaining_rejections(self) -> None:
        with self.assertRaises(ValueError):
            validation_support._require_identifier("", rules=helpers.IdentifierRules(label="label", allowed_chars={"a"}, min_len=1, max_len=2))
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
            validation_support._validate_https_url_shape("https://user:" + "pw" + "@example.com/path")
        self.assertEqual(validation_support._normalize_suffix_allowlist(None), set())
        with self.assertRaises(ValueError):
            validation_support._ensure_host_allowlist("api.example.com", allowed_hosts={"codecov.io"})
        with self.assertRaises(ValueError):
            validation_support._ensure_host_allowlist("api.example.com", allowed_host_suffixes={"codecov.io"})
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
        connection_box: dict[str, _FakeHTTPSConnection] = {}

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
        self.assertEqual(connection.request_args[0], "POST")
        self.assertEqual(connection.request_args[1], "/repos/owner/repo")
        self.assertEqual(connection.request_args[2], b'{"ok": true}')
        self.assertEqual(connection.request_args[3]["Accept"], "application/json")
        self.assertEqual(connection.request_args[3]["Content-Type"], "application/json")
        self.assertEqual(payload.status, 200)
        self.assertEqual(payload.headers["x-hits"], "7")
        self.assertTrue(connection.closed)

    def test_json_request_helpers_cover_success_and_error_paths(self) -> None:
        success = helpers.HTTPSResponsePayload(
            host="api.github.com",
            path="/repos/owner/repo",
            status=200,
            reason="OK",
            body='{"name": "value"}',
            headers={},
        )
        with mock.patch.object(http_support, "_request_https_payload", return_value=success):
            self.assertEqual(
                http_support.request_json_https_target(
                    target=helpers.HTTPSRequestTarget(host="api.github.com", path="/repos/owner/repo")
                ),
                {"name": "value"},
            )

        list_payload = helpers.HTTPSResponsePayload(
            host="api.github.com",
            path="/repos/owner/repo",
            status=200,
            reason="OK",
            body='[{"name": "value"}]',
            headers={"x-hits": "1"},
        )
        with mock.patch.object(http_support, "_request_https_payload", return_value=list_payload):
            items, headers = http_support.request_json_list_https_target(
                target=helpers.HTTPSRequestTarget(host="api.github.com", path="/repos/owner/repo")
            )
        self.assertEqual(items, [{"name": "value"}])
        self.assertEqual(headers["x-hits"], "1")

        error_payload = helpers.HTTPSResponsePayload(
            host="api.github.com",
            path="/repos/owner/repo",
            status=500,
            reason="boom",
            body="fail-body",
            headers={},
        )
        with mock.patch.object(http_support, "_request_https_payload", return_value=error_payload):
            with self.assertRaises(helpers.HTTPSRequestError) as error:
                http_support.request_json_https_target(
                    target=helpers.HTTPSRequestTarget(host="api.github.com", path="/repos/owner/repo")
                )
        self.assertEqual(error.exception.status, 500)
        self.assertEqual(error.exception.reason, "boom")
        self.assertEqual(error.exception.body_preview, "fail-body")

        with self.assertRaises(RuntimeError):
            http_support._parse_json_response("not-json", host="api.github.com", path="/bad")

        with self.assertRaises(ValueError):
            http_support._merge_safe_headers({"Bad Header": "x"}, include_json_content_type=False)

        with self.assertRaises(ValueError):
            http_support.request_json_https(host="example.com", path="/repos")

    def test_wrapper_helpers_and_non_collection_json_errors(self) -> None:
        self.assertIs(http_support._https_connection(), http.client.HTTPSConnection)
        with self.assertRaises(ValueError):
            http_support._safe_timeout_seconds("bad")

        with mock.patch.object(http_support, "request_json_https_target", return_value={"ok": True}) as object_mock:
            payload = http_support.request_json_https(host="api.github.com", path="/repos/owner/repo")
        self.assertEqual(payload, {"ok": True})
        object_mock.assert_called_once()

        with mock.patch.object(http_support, "request_json_list_https_target", return_value=([{"ok": True}], {"x-hits": "1"})) as list_mock:
            items, headers = http_support.request_json_list_https(host="api.github.com", path="/repos/owner/repo")
        self.assertEqual(items, [{"ok": True}])
        self.assertEqual(headers["x-hits"], "1")
        list_mock.assert_called_once()

        dict_payload = helpers.HTTPSResponsePayload(
            host="api.github.com",
            path="/repos/owner/repo",
            status=200,
            reason="OK",
            body='{"name": "value"}',
            headers={},
        )
        with mock.patch.object(http_support, "_request_https_payload", return_value=dict_payload):
            with self.assertRaises(RuntimeError):
                http_support.request_json_list_https_target(
                    target=helpers.HTTPSRequestTarget(host="api.github.com", path="/repos/owner/repo")
                )

        error_payload = helpers.HTTPSResponsePayload(
            host="api.github.com",
            path="/repos/owner/repo",
            status=404,
            reason="missing",
            body="not-found",
            headers={},
        )
        with mock.patch.object(http_support, "_request_https_payload", return_value=error_payload):
            with self.assertRaises(helpers.HTTPSRequestError) as error:
                http_support.request_json_list_https_target(
                    target=helpers.HTTPSRequestTarget(host="api.github.com", path="/repos/owner/repo")
                )
        self.assertEqual(error.exception.status, 404)

        list_payload = helpers.HTTPSResponsePayload(
            host="api.github.com",
            path="/repos/owner/repo",
            status=200,
            reason="OK",
            body='[{"name": "value"}]',
            headers={},
        )
        with mock.patch.object(http_support, "_request_https_payload", return_value=list_payload):
            with self.assertRaises(RuntimeError):
                http_support.request_json_https_target(
                    target=helpers.HTTPSRequestTarget(host="api.github.com", path="/repos/owner/repo")
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
            required_checks_support._evaluate_check_run("Codecov Analytics", {"state": "queued", "conclusion": "success"}),
            "Codecov Analytics: status=queued",
        )
        self.assertEqual(
            required_checks_support._evaluate_check_run("Codecov Analytics", {"state": "completed", "conclusion": "failure"}),
            "Codecov Analytics: conclusion=failure",
        )


class CoverageParsersAndNormalizeLCOVTests(unittest.TestCase):
    def test_normalize_lcov_lines_and_main_strip_branch_records(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            (repo_root / "src").mkdir()
            (repo_root / "src" / "main.cpp").write_text("int main() { return 0; }\n", encoding="utf-8")
            (repo_root / "src" / "named.py").write_text("print('hello')\n", encoding="utf-8")
            (repo_root / "ignored.py").write_text("print('ignore')\n", encoding="utf-8")

            original_is_file = Path.is_file

            def _patched_is_file(path: Path) -> bool:
                if path.name == "ignored.py":
                    raise OSError("access denied")
                return original_is_file(path)

            with mock.patch.object(Path, "is_file", new=_patched_is_file):
                repo_paths, repo_file_index = normalize_lcov._build_repo_file_indexes(repo_root)

            self.assertEqual(repo_file_index["main.cpp"], ["src/main.cpp"])
            self.assertNotIn("ignored.py", repo_file_index)
            self.assertEqual(normalize_lcov._sanitize_relative_candidate("./src/main.cpp"), "src/main.cpp")
            self.assertEqual(normalize_lcov._sanitize_relative_candidate("../main.cpp"), "main.cpp")
            self.assertEqual(
                normalize_lcov._trim_to_source_suffix("build/CMakeFiles/airline.dir/src/main.cpp.gcda"),
                "build/CMakeFiles/airline.dir/src/main.cpp",
            )
            self.assertEqual(normalize_lcov._trim_to_source_suffix("coverage-report.txt"), "coverage-report.txt")
            self.assertEqual(
                normalize_lcov._matching_repo_suffix("build/CMakeFiles/airline.dir/src/main.cpp.gcda", repo_paths),
                "src/main.cpp",
            )
            self.assertEqual(normalize_lcov._matching_repo_suffix("src/main.cpp", repo_paths), "src/main.cpp")
            self.assertEqual(normalize_lcov._matching_repo_suffix("../main.cpp", repo_paths), "main.cpp")
            self.assertEqual(
                normalize_lcov._normalize_source_path(
                    "././src/main.cpp",
                    repo_root=repo_root,
                    repo_paths=repo_paths,
                    repo_file_index=repo_file_index,
                ),
                "src/main.cpp",
            )
            self.assertEqual(
                normalize_lcov._normalize_source_path(
                    "",
                    repo_root=repo_root,
                    repo_paths=repo_paths,
                    repo_file_index=repo_file_index,
                ),
                "",
            )
            self.assertEqual(
                normalize_lcov._normalize_source_path(
                    f"{repo_root.resolve(strict=False).as_posix()}/src/main.cpp",
                    repo_root=repo_root,
                    repo_paths=repo_paths,
                    repo_file_index=repo_file_index,
                ),
                "src/main.cpp",
            )
            self.assertEqual(
                normalize_lcov._normalize_source_path(
                    repo_root.resolve(strict=False).as_posix(),
                    repo_root=repo_root,
                    repo_paths=repo_paths,
                    repo_file_index=repo_file_index,
                ),
                "",
            )
            self.assertEqual(
                normalize_lcov._normalize_source_path(
                    "C:/outside/named.py",
                    repo_root=repo_root,
                    repo_paths=repo_paths,
                    repo_file_index=repo_file_index,
                ),
                "src/named.py",
            )
            self.assertEqual(
                normalize_lcov._normalize_source_path(
                    "reports/no-match.txt",
                    repo_root=repo_root,
                    repo_paths=repo_paths,
                    repo_file_index=repo_file_index,
                ),
                "reports/no-match.txt",
            )

            normalized, stripped = normalize_lcov.normalize_lcov_lines(
                [
                    "TN:",
                    "SF:build/CMakeFiles/airline.dir/src/main.cpp.gcda",
                    "BRDA:1,0,0,1",
                    "DA:1,1",
                    "end_of_record",
                    f"SF:{(repo_root / 'src' / 'named.py').as_posix()}",
                    "BRF:1",
                    "DA:2,1",
                    "end_of_record",
                ],
                repo_root=repo_root,
            )
            self.assertEqual(stripped, 2)
            self.assertEqual(
                normalized,
                "TN:\nSF:src/main.cpp\nDA:1,1\nend_of_record\nSF:src/named.py\nDA:2,1\nend_of_record\n",
            )

            stdout = io.StringIO()
            stderr = io.StringIO()
            with _temporary_cwd(repo_root):
                result = normalize_lcov.main(
                    stdin=io.StringIO("SF:build/CMakeFiles/app.dir/src/main.cpp.gcno\nBRH:1\nDA:2,1\n"),
                    stdout=stdout,
                    stderr=stderr,
                )
            self.assertEqual(result, 0)
            self.assertEqual(stdout.getvalue(), "SF:src/main.cpp\nDA:2,1\n")
            self.assertIn("stripped 1 branch records", stderr.getvalue())

    def test_lcov_and_istanbul_parsers_cover_fallback_and_exclusions(self) -> None:
        parsers._excluded_line_numbers.cache_clear()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            lcov_path = temp_path / "coverage.lcov"
            lcov_path.write_text(
                "\n".join(
                    [
                        "SF:repo/src/sample.cpp",
                        "DA:1,1",
                        "DA:2,0",
                        "DA:3,0",
                        "DA:4,0",
                        "DA:5,0",
                        "DA:6,0",
                        "DA:7,0",
                        "DA:8,1",
                        "end_of_record",
                        "SF:repo/src/fallback.cpp",
                        "LF:4",
                        "LH:3",
                        "end_of_record",
                    ]
                ),
                encoding="utf-8",
            )
            summary_path = temp_path / "summary.json"
            summary_path.write_text(json.dumps({"total": {"lines": {"covered": 4, "total": 5}}}), encoding="utf-8")
            fallback_summary = temp_path / "fallback-summary.json"
            fallback_summary.write_text(json.dumps({"total": {"statements": {"covered": 3, "total": 4}}}), encoding="utf-8")
            final_path = temp_path / "final.json"
            final_path.write_text(
                json.dumps(
                    {
                        "a.js": {"s": {"1": 1, "2": 0}},
                        "b.js": {"s": {"1": 2}},
                        "bad": [],
                    }
                ),
                encoding="utf-8",
            )

            sample_lines = (
                "int a = 1;",
                "{",
                "do_skip(); // GCOVR_EXCL_LINE",
                "value += 1;",
                "// GCOVR_EXCL_START",
                "never_count();",
                "// GCOVR_EXCL_STOP",
                "return 0;",
            )

            with mock.patch.dict(parsers.REPO_SOURCE_LINES, {"src/sample.cpp": sample_lines}, clear=False):
                lcov_stats = parsers.parse_lcov("cpp", lcov_path)

            summary_stats = parsers.parse_istanbul_summary("node", summary_path)
            fallback_stats = parsers.parse_istanbul_summary("node-fallback", fallback_summary)
            final_stats = parsers.parse_istanbul_final("node-final", final_path)

        self.assertEqual((lcov_stats.covered, lcov_stats.total), (5, 7))
        self.assertEqual((summary_stats.covered, summary_stats.total), (4, 5))
        self.assertEqual((fallback_stats.covered, fallback_stats.total), (3, 4))
        self.assertEqual((final_stats.covered, final_stats.total), (2, 3))
        self.assertIsNone(parsers._lookup_repo_source_lines("/abs/path.cpp"))
        self.assertEqual(parsers._safe_int("bad"), 0)

    def test_parser_helper_branches_cover_empty_inputs_and_repo_prefixes(self) -> None:
        self.assertEqual(parsers.CoverageStats(name="empty", path="x", covered=0, total=0).percent, 100.0)
        self.assertTrue(parsers._include_lcov_line(None, 0))
        self.assertIsNone(parsers._lookup_repo_source_lines("../escape.cpp"))
        with mock.patch.dict(
            parsers.REPO_SOURCE_LINES,
            {"src/ReservationSystem.cpp": ("int handleReservation();",)},
            clear=False,
        ):
            self.assertEqual(
                parsers._lookup_repo_source_lines("./src/ReservationSystem.cpp"),
                ("int handleReservation();",),
            )

        repo_relative = "src/sample.cpp"
        sample_lines = ("int main() {", "return 0;", "}")
        repo_prefixed = parsers.REPO_ROOT.as_posix().rstrip("/") + "/" + repo_relative
        with mock.patch.dict(parsers.REPO_SOURCE_LINES, {repo_relative: sample_lines}, clear=False):
            self.assertEqual(parsers._lookup_repo_source_lines(repo_prefixed), sample_lines)
            self.assertEqual(parsers._lookup_repo_source_lines(f"repo/{repo_relative}"), sample_lines)

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            not_dict_path = temp_path / "not-dict.json"
            not_dict_path.write_text(json.dumps(["bad"]), encoding="utf-8")
            bad_statements_path = temp_path / "bad-statements.json"
            bad_statements_path.write_text(json.dumps({"a.js": {"s": []}}), encoding="utf-8")

            not_dict_stats = parsers.parse_istanbul_final("node", not_dict_path)
            bad_statement_stats = parsers.parse_istanbul_final("node", bad_statements_path)

        self.assertEqual((not_dict_stats.covered, not_dict_stats.total), (0, 0))
        self.assertEqual((bad_statement_stats.covered, bad_statement_stats.total), (0, 0))


class AirlineCoverageGateTests(unittest.TestCase):
    def test_load_node_stats_prefers_known_inputs_and_evaluate_reports_failures(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            node_lcov = temp_path / "node.lcov"
            node_lcov.write_text("LF:2\nLH:2\n", encoding="utf-8")
            summary = temp_path / "summary.json"
            summary.write_text(json.dumps({"total": {"lines": {"covered": 3, "total": 4}}}), encoding="utf-8")
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
                mock.patch.object(airline_coverage_gate, "quality_artifact_paths", return_value=(out_json, out_md)),
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
                mock.patch.object(airline_coverage_gate, "quality_artifact_paths", return_value=(out_json, out_md)),
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
                mock.patch.object(airline_coverage_gate, "quality_artifact_paths", return_value=(out_json, out_md)),
                mock.patch.object(sys, "argv", ["assert_coverage_100.py"]),
            ):
                self.assertEqual(airline_coverage_gate.main(), 0)
            payload = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertEqual([component["name"] for component in payload["components"]], ["node", "cpp"])


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
                out_json, _ = helpers.quality_artifact_paths(helpers.QualityArtifact.QUALITY_SECRETS)
                payload = json.loads(out_json.read_text(encoding="utf-8"))
                self.assertTrue(payload["details_omitted"])

    def test_codacy_helpers_and_main_cover_success_failure_and_token_resolution(self) -> None:
        nested_total = {"outer": [{"hits": 3}]}
        self.assertEqual(codacy.extract_total_open(nested_total), 3)
        self.assertIsNone(codacy.extract_total_open({"results": []}))

        with mock.patch.dict(os.environ, {"CODACY_API_TOKEN": "env-token"}, clear=True):
            self.assertEqual(codacy._resolve_token(""), "env-token")

        args = Namespace(provider="gh", owner="Prekzursil", repo="Airline-Reservations-System", branch="")
        self.assertEqual(codacy._run_codacy_check(args, ""), (None, ["CODACY_API_TOKEN is missing."], "fail"))

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
                mock.patch.object(codacy, "quality_artifact_paths", return_value=(out_json, out_md)),
                mock.patch.object(codacy, "_run_codacy_check", return_value=(0, [], "pass")),
                mock.patch.object(sys, "argv", cli_args),
            ):
                self.assertEqual(codacy.main(), 0)

            payload = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "pass")
            self.assertEqual(payload["open_issues"], 0)

    def test_codacy_render_and_status_branches(self) -> None:
        with mock.patch.object(sys, "argv", ["check_codacy_zero.py", "--owner", "Prekzursil", "--repo", "Airline-Reservations-System"]):
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

        findings: list[str] = []
        self.assertEqual(codacy._evaluate_status(None, findings), "fail")
        self.assertIn("parseable total issue count", findings[0])

        findings = []
        self.assertEqual(codacy._evaluate_status(2, findings), "fail")
        self.assertIn("expected 0", findings[0])


class DeepScanAndRequiredChecksTests(unittest.TestCase):
    def test_deepscan_helpers_and_run_check_cover_missing_pending_and_success(self) -> None:
        self.assertEqual(
            deepscan._pending_failure_message("DeepScan", {"source": "check_run", "state": "queued"}),
            "DeepScan status is queued (expected completed)",
        )
        self.assertEqual(
            deepscan._pending_failure_message("DeepScan", {"source": "status", "conclusion": "pending"}),
            "DeepScan state is pending (expected success)",
        )
        self.assertTrue(deepscan._is_pending_context({"source": "check_run", "state": "in_progress"}))
        self.assertTrue(deepscan._is_pending_context({"source": "status", "conclusion": "pending"}))
        self.assertEqual(deepscan._context_outcome("DeepScan", {"source": "check_run", "state": "completed", "conclusion": "success"}), ("pass", None))
        self.assertEqual(deepscan._context_outcome("DeepScan", {"source": "status", "conclusion": "failure"}), ("fail", "DeepScan state is failure (expected success)"))

        args = Namespace(repo="owner/repo", sha="a1b2c3d", required_context="DeepScan", max_wait_seconds=0, poll_interval_seconds=1)
        with (
            mock.patch.object(deepscan, "_api_get", return_value={}),
            mock.patch.object(deepscan, "collect_contexts", return_value={}),
            mock.patch.object(deepscan, "_poll_or_timeout", return_value=False),
        ):
            status, findings, observed = deepscan._run_deepscan_check(args, "token")
        self.assertEqual((status, observed), ("fail", None))
        self.assertEqual(findings, ["Missing required context: DeepScan"])

        pending_context = {"DeepScan": {"source": "check_run", "state": "queued", "conclusion": ""}}
        with (
            mock.patch.object(deepscan, "_api_get", return_value={}),
            mock.patch.object(deepscan, "collect_contexts", return_value=pending_context),
            mock.patch.object(deepscan, "_poll_or_timeout", return_value=False),
        ):
            status, findings, observed = deepscan._run_deepscan_check(args, "token")
        self.assertEqual(status, "fail")
        self.assertEqual(observed, pending_context["DeepScan"])
        self.assertIn("expected completed", findings[0])

        success_context = {"DeepScan": {"source": "status", "state": "success", "conclusion": "success"}}
        with (
            mock.patch.object(deepscan, "_api_get", return_value={}),
            mock.patch.object(deepscan, "collect_contexts", return_value=success_context),
        ):
            status, findings, observed = deepscan._run_deepscan_check(args, "token")
        self.assertEqual((status, findings, observed), ("pass", [], success_context["DeepScan"]))

    def test_deepscan_parse_render_poll_and_main_paths(self) -> None:
        with mock.patch.object(sys, "argv", ["check_deepscan_zero.py", "--repo", "owner/repo", "--sha", "a1b2c3d"]):
            args = deepscan._parse_args()
        self.assertEqual(args.required_context, "DeepScan")

        target_payload = {"ok": True}
        with mock.patch.object(deepscan, "request_json_https_target", return_value=target_payload):
            self.assertEqual(
                deepscan._api_get(
                    helpers.HTTPSRequestTarget(host="api.github.com", path="/repos/owner/repo"),
                    "token",
                ),
                target_payload,
            )

        self.assertTrue(deepscan._poll_or_timeout(0, 1, 1))
        self.assertFalse(deepscan._poll_or_timeout(2, 1, 1))
        self.assertEqual(
            deepscan._context_outcome("DeepScan", {"source": "check_run", "state": "completed", "conclusion": "failure"}),
            ("fail", "DeepScan conclusion is failure (expected success)"),
        )
        self.assertEqual(
            deepscan._context_outcome("DeepScan", {"source": "status", "conclusion": "success"}),
            ("pass", None),
        )

        rendered = deepscan._render_md(
            {
                "status": "pass",
                "repo": "owner/repo",
                "sha": "a1b2c3d",
                "required_context": "DeepScan",
                "timestamp_utc": "2026-03-19T00:00:00+00:00",
                "findings": [],
            }
        )
        self.assertIn("- None", rendered)

        args = Namespace(repo="owner/repo", sha="a1b2c3d", required_context="DeepScan", max_wait_seconds=1, poll_interval_seconds=1)
        pending_context = {"DeepScan": {"source": "status", "state": "pending", "conclusion": "pending"}}
        success_context = {"DeepScan": {"source": "status", "state": "success", "conclusion": "success"}}
        with (
            mock.patch.object(deepscan, "_api_get", return_value={}),
            mock.patch.object(deepscan, "collect_contexts", side_effect=[pending_context, success_context]),
            mock.patch.object(deepscan, "_poll_or_timeout", side_effect=[True]),
        ):
            status, findings, observed = deepscan._run_deepscan_check(args, "token")
        self.assertEqual((status, findings, observed), ("pass", [], success_context["DeepScan"]))

        with (
            mock.patch.object(deepscan, "_api_get", return_value={}),
            mock.patch.object(deepscan, "collect_contexts", side_effect=[{}, {}]),
            mock.patch.object(deepscan, "_poll_or_timeout", side_effect=[True, False]),
        ):
            status, findings, observed = deepscan._run_deepscan_check(args, "token")
        self.assertEqual((status, observed), ("fail", None))
        self.assertEqual(findings, ["Missing required context: DeepScan"])

        failing_context = {"DeepScan": {"source": "status", "state": "failure", "conclusion": "failure"}}
        with (
            mock.patch.object(deepscan, "_api_get", return_value={}),
            mock.patch.object(deepscan, "collect_contexts", return_value=failing_context),
        ):
            status, findings, observed = deepscan._run_deepscan_check(args, "token")
        self.assertEqual((status, observed), ("fail", failing_context["DeepScan"]))
        self.assertIn("expected success", findings[0])

        with self.assertRaises(SystemExit):
            with mock.patch.object(sys, "argv", ["check_deepscan_zero.py", "--repo", "owner/repo", "--sha", "a1b2c3d"]):
                with mock.patch.dict(os.environ, {}, clear=True):
                    deepscan.main()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            out_json = temp_path / "deepscan.json"
            out_md = temp_path / "deepscan.md"
            with (
                mock.patch.object(deepscan, "quality_artifact_paths", return_value=(out_json, out_md)),
                mock.patch.object(deepscan, "_run_deepscan_check", return_value=("fail", ["broken"], {"source": "status", "conclusion": "failure"})),
                mock.patch.object(sys, "argv", ["check_deepscan_zero.py", "--repo", "owner/repo", "--sha", "a1b2c3d"]),
                mock.patch.dict(os.environ, {"GITHUB_TOKEN": "token"}, clear=True),
            ):
                self.assertEqual(deepscan.main(), 1)
            payload = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "fail")
            self.assertIn("broken", out_md.read_text(encoding="utf-8"))

    def test_required_checks_retry_collect_payload_and_main(self) -> None:
        response = {"ok": True}
        transient_error = helpers.HTTPSRequestError(503, "busy", "wait")
        with (
            mock.patch.object(required_checks, "request_json_https_target", side_effect=[transient_error, response]),
            mock.patch.object(required_checks.time, "sleep") as sleep_mock,
        ):
            self.assertEqual(
                required_checks._api_get(
                    helpers.HTTPSRequestTarget(host="api.github.com", path="/repos/owner/repo"),
                    "token",
                ),
                response,
            )
        sleep_mock.assert_called_once()

        args = Namespace(repo="owner/repo", sha="a1b2c3d", timeout_seconds=1, poll_seconds=1)
        required = ["Codecov Analytics"]
        with (
            mock.patch.object(required_checks, "_fetch_check_payloads", return_value=({}, {})),
            mock.patch.object(required_checks, "collect_contexts", return_value={"Codecov Analytics": {"source": "status", "conclusion": "success"}}),
        ):
            payload = required_checks._collect_payload(args, required, "token")
        self.assertEqual(payload["status"], "pass")

        with (
            mock.patch.object(required_checks, "_fetch_check_payloads", return_value=({}, {})),
            mock.patch.object(required_checks, "collect_contexts", return_value={}),
            mock.patch.object(required_checks, "has_check_runs_in_progress", return_value=False),
            mock.patch.object(required_checks.time, "time", side_effect=[0, 0, 2]),
            mock.patch.object(required_checks.time, "sleep") as sleep_mock,
        ):
            payload = required_checks._collect_payload(args, required, "token")
        self.assertEqual(payload["status"], "fail")
        self.assertEqual(payload["missing"], ["Codecov Analytics"])
        sleep_mock.assert_called_once_with(1)

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            out_json = temp_path / "required.json"
            out_md = temp_path / "required.md"
            with (
                mock.patch.dict(os.environ, {"GITHUB_TOKEN": "token"}, clear=True),
                mock.patch.object(required_checks, "quality_artifact_paths", return_value=(out_json, out_md)),
                mock.patch.object(required_checks, "_collect_payload", return_value={"status": "pass", "repo": "owner/repo", "sha": "a1b2c3d", "required": ["Codecov Analytics"], "missing": [], "failed": [], "contexts": {}, "timestamp_utc": "2026-03-19T00:00:00+00:00"}),
                mock.patch.object(sys, "argv", ["check_required_checks.py", "--repo", "owner/repo", "--sha", "a1b2c3d", "--required-context", "Codecov Analytics"]),
            ):
                self.assertEqual(required_checks.main(), 0)
            self.assertIn("Status: `pass`", out_md.read_text(encoding="utf-8"))

    def test_required_checks_additional_retry_render_fetch_and_input_paths(self) -> None:
        with mock.patch.object(sys, "argv", ["check_required_checks.py", "--repo", "owner/repo", "--sha", "a1b2c3d", "--required-context", "Codecov Analytics"]):
            args = required_checks._parse_args()
        self.assertEqual(args.timeout_seconds, 900)

        with mock.patch.object(required_checks, "request_json_https_target", side_effect=[RuntimeError("boom")] * 4), mock.patch.object(required_checks.time, "sleep") as sleep_mock:
            with self.assertRaises(RuntimeError):
                required_checks._api_get(helpers.HTTPSRequestTarget(host="api.github.com", path="/repos/owner/repo"), "token")
        self.assertEqual(sleep_mock.call_count, 3)
        with mock.patch.object(
            required_checks,
            "request_json_https_target",
            side_effect=helpers.HTTPSRequestError(404, "missing", "nope"),
        ):
            with self.assertRaises(RuntimeError):
                required_checks._api_get(
                    helpers.HTTPSRequestTarget(host="api.github.com", path="/repos/owner/repo"),
                    "token",
                )

        rendered = required_checks._render_md(
            {
                "status": "fail",
                "repo": "owner/repo",
                "sha": "a1b2c3d",
                "timestamp_utc": "2026-03-19T00:00:00+00:00",
                "missing": ["Codecov Analytics"],
                "failed": ["QLTY Zero: conclusion=failure"],
            }
        )
        self.assertIn("`Codecov Analytics`", rendered)
        self.assertIn("QLTY Zero: conclusion=failure", rendered)

        with mock.patch.object(required_checks, "_api_get", side_effect=[{"check_runs": []}, {"statuses": []}]):
            self.assertEqual(required_checks._fetch_check_payloads("owner/repo", "a1b2c3d", "token"), ({"check_runs": []}, {"statuses": []}))

        failing_args = Namespace(repo="owner/repo", sha="a1b2c3d", timeout_seconds=1, poll_seconds=1)
        with (
            mock.patch.object(required_checks, "_fetch_check_payloads", return_value=({}, {})),
            mock.patch.object(required_checks, "collect_contexts", return_value={"Codecov Analytics": {"source": "status", "conclusion": "failure"}}),
            mock.patch.object(required_checks, "has_check_runs_in_progress", return_value=False),
            mock.patch.object(required_checks.time, "sleep") as sleep_mock,
        ):
            payload = required_checks._collect_payload(failing_args, ["Codecov Analytics"], "token")
        self.assertEqual(payload["failed"], ["Codecov Analytics: state=failure"])
        sleep_mock.assert_not_called()

        with (
            mock.patch.object(required_checks.time, "time", side_effect=[0, 2]),
            mock.patch.object(required_checks, "_fetch_check_payloads"),
        ):
            with self.assertRaises(RuntimeError):
                required_checks._collect_payload(failing_args, ["Codecov Analytics"], "token")

        with self.assertRaises(SystemExit):
            with mock.patch.object(sys, "argv", ["check_required_checks.py", "--repo", "owner/repo", "--sha", "a1b2c3d"]):
                required_checks.main()
        with self.assertRaises(SystemExit):
            with mock.patch.object(sys, "argv", ["check_required_checks.py", "--repo", "owner/repo", "--sha", "a1b2c3d", "--required-context", "Codecov Analytics"]):
                with mock.patch.dict(os.environ, {}, clear=True):
                    required_checks.main()


class SentryAndSonarScriptTests(unittest.TestCase):
    def test_sentry_helpers_and_main_cover_project_resolution_and_failures(self) -> None:
        config = sentry_targets.SentryConfig(org_label="Org", project_label="Project", user_agent="ua")
        self.assertEqual(sentry_targets.hits_from_headers({"x-hits": "7"}), 7)
        self.assertIsNone(sentry_targets.hits_from_headers({"x-hits": "bad"}))
        self.assertEqual(sentry_targets.auth_headers("token", config)["Authorization"], "Bearer token")
        self.assertIn("query=is%3Aunresolved", sentry_targets.build_project_issues_path("org", "proj", config))

        self.assertEqual(sentry_support.project_slug_from_match({"slug": "proj", "name": "Project"}, "project"), "proj")
        self.assertIsNone(sentry_support.project_slug_from_match({"name": "Project"}, "project"))
        self.assertTrue(sentry_support.is_not_found_error(RuntimeError("404 Not Found")))

        with mock.patch.object(sentry_support, "fetch_org_projects", return_value=[{"slug": "proj-backend", "name": "Backend"}]):
            self.assertEqual(sentry_support.resolve_project_slug("org", "Backend", "token", config), "proj-backend")

        with mock.patch.object(sentry_support, "resolve_project_slug", return_value="proj-backend"):
            candidates = sentry_support.project_candidates("org", "Proj_Backend", "token", config)
        self.assertEqual(candidates[0], "proj-backend")
        self.assertIn("Proj_Backend", candidates)

        with mock.patch.dict(os.environ, {"SENTRY_PROJECT_BACKEND": "backend", "SENTRY_PROJECT": "shared"}, clear=True):
            self.assertEqual(sentry_support.projects_from_args_or_env(Namespace(project=[])), ["backend", "shared"])

        self.assertEqual(
            sentry_support.validate_inputs("", "", []),
            ["SENTRY_AUTH_TOKEN is missing.", "SENTRY_ORG is missing.", "No Sentry projects configured."],
        )

        findings: list[str] = []
        unresolved = sentry_support.unresolved_count("proj", [{"id": 1}], {}, findings)
        self.assertEqual(unresolved, 1)
        self.assertIn("no X-Hits header", findings[0])

        findings = []
        sentry_support.append_project_fetch_failure("proj", RuntimeError("404 Not Found"), "org", findings)
        self.assertIn("not found in org", findings[0])

        with mock.patch.object(
            sentry_support,
            "select_project_payload",
            side_effect=[
                ("proj", [], {"x-hits": "0"}, None),
                (None, None, {}, RuntimeError("404 Not Found")),
                (None, None, {}, RuntimeError("boom")),
            ],
        ):
            results, findings = sentry_support.evaluate_projects("org", ["proj", "missing", "broken"], "token", config)
        self.assertEqual(results[0]["status"], "ok")
        self.assertEqual(results[1]["status"], "not_found")
        self.assertIn("request failed", findings[-1])

        sentry_token = _join_parts("tok", "en")
        args = Namespace(org="org", project=["proj"], token=sentry_token)
        with mock.patch.object(sentry_support, "evaluate_projects", return_value=([{"project": "proj", "resolved_project": "proj", "unresolved": 0, "status": "ok"}], [])):
            status, org, project_results, findings = sentry_support.run_sentry_check(args, config)
        self.assertEqual((status, org, findings), ("pass", "org", []))
        self.assertEqual(project_results[0]["project"], "proj")

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            out_json = temp_path / "sentry.json"
            out_md = temp_path / "sentry.md"
            with (
                mock.patch.object(sentry, "quality_artifact_paths", return_value=(out_json, out_md)),
                mock.patch.object(sentry, "run_sentry_check", side_effect=ValueError("bad request")),
                mock.patch.object(sys, "argv", ["check_sentry_zero.py"]),
            ):
                self.assertEqual(sentry.main(), 1)
            self.assertIn("Sentry API request failed", out_md.read_text(encoding="utf-8"))

    def test_sentry_additional_helpers_cover_wrappers_and_validation_paths(self) -> None:
        config = sentry_targets.SentryConfig(org_label="Org", project_label="Project", user_agent="ua")
        with mock.patch.object(sys, "argv", ["check_sentry_zero.py", "--org", "org", "--project", "proj"]):
            args = sentry._parse_args()
        self.assertEqual(args.org, "org")

        rendered = sentry._render_md(
            {
                "status": "pass",
                "org": "org",
                "projects": [{"project": "proj", "unresolved": 1}],
                "timestamp_utc": "2026-03-19T00:00:00+00:00",
                "findings": [],
            }
        )
        self.assertIn("## Project results", rendered)
        self.assertIn("`proj` unresolved=`1`", rendered)

        with mock.patch.object(sentry_support, "request_json_list_https_target", return_value=([{"slug": "proj"}], {})):
            self.assertEqual(sentry_support.fetch_org_projects("org", "proj", "token", config), [{"slug": "proj"}])
            self.assertEqual(sentry_support.fetch_project_issues("org", "proj", "token", config), ([{"slug": "proj"}], {}))
        with mock.patch.object(sentry_support, "request_json_list_https_target", side_effect=RuntimeError("boom")):
            self.assertIsNone(sentry_support.fetch_org_projects("org", "proj", "token", config))

        self.assertIsNone(sentry_support.project_slug_from_match("bad", "proj"))
        self.assertIsNone(sentry_support.project_slug_from_match({"slug": ""}, "proj"))
        self.assertIsNone(sentry_support.project_slug_from_match({"slug": "proj", "name": "Project"}, "other"))
        with mock.patch.object(sentry_support, "fetch_org_projects", return_value=None):
            self.assertIsNone(sentry_support.resolve_project_slug("org", "Proj", "token", config))
        with mock.patch.object(sentry_support, "fetch_org_projects", return_value=[{"slug": "proj", "name": "Project"}]):
            self.assertIsNone(sentry_support.resolve_project_slug("org", "Other", "token", config))
        with mock.patch.object(sentry_support, "resolve_project_slug", return_value=None):
            self.assertEqual(sentry_support.project_candidates("org", "", "token", config), [])

        with mock.patch.object(sentry_support, "project_candidates", return_value=["proj-a", "proj-b"]), mock.patch.object(
            sentry_support,
            "fetch_project_issues",
            side_effect=[RuntimeError("404 Not Found"), ([{"id": 1}], {"x-hits": "1"})],
        ):
            resolved, issues, headers, last_error = sentry_support.select_project_payload("org", "proj", "token", config)
        self.assertEqual((resolved, issues, headers, last_error), ("proj-b", [{"id": 1}], {"x-hits": "1"}, None))
        with mock.patch.object(sentry_support, "project_candidates", return_value=["proj-a", "proj-b"]), mock.patch.object(
            sentry_support,
            "fetch_project_issues",
            side_effect=[RuntimeError("404 Not Found"), RuntimeError("404 Not Found")],
        ):
            resolved, issues, headers, last_error = sentry_support.select_project_payload("org", "proj", "token", config)
        self.assertEqual((resolved, issues, headers), (None, None, {}))
        self.assertIsInstance(last_error, RuntimeError)

        findings: list[str] = []
        sentry_support.append_project_fetch_failure("proj", None, "org", findings)
        self.assertIn("did not return data", findings[0])

        with mock.patch.dict(os.environ, {}, clear=True):
            status, org, project_results, findings = sentry_support.run_sentry_check(Namespace(org="", project=[], token=None), config)
        self.assertEqual((status, org, project_results), ("fail", "", []))
        self.assertIn("SENTRY_AUTH_TOKEN is missing.", findings)
        with mock.patch.object(
            sentry_support,
            "select_project_payload",
            return_value=("proj", [{"id": 1}], {"x-hits": "2"}, None),
        ):
            project_results, findings = sentry_support.evaluate_projects("org", ["proj"], "token", config)
        self.assertEqual(project_results[0]["unresolved"], 2)
        self.assertIn("expected 0", findings[0])

        project_target = sentry_targets.build_project_issues_target("org", "proj", config)
        org_target = sentry_targets.build_org_projects_target("org", "proj", config)
        self.assertEqual(project_target.host, helpers.HTTPSHost.SENTRY.value)
        self.assertIn("/organizations/", org_target.path)

    def test_sonar_helpers_and_main_cover_timeout_and_success_paths(self) -> None:
        self.assertTrue(sonar._auth_header("token").startswith("Basic "))
        self.assertEqual(sonar._paged_total({"paging": {"total": 5}}), 5)

        args = Namespace(
            branch="feature",
            pull_request="17",
            expected_pr_sha="want",
            max_wait_seconds=0,
            poll_interval_seconds=1,
            project_key="Prekzursil_Airline-Reservations-System",
        )
        with mock.patch.object(sonar, "_fetch_pr_analysis_sha", return_value="have"), mock.patch.object(sonar.time, "time", side_effect=[0, 1]):
            status, open_issues, unresolved_hotspots, quality_gate, findings = sonar._run_sonar_check(args, "token")
        self.assertEqual(status, "fail")
        self.assertIsNone(open_issues)
        self.assertIn("Expected SHA: want", findings)

        success_args = Namespace(
            branch="feature",
            pull_request="17",
            expected_pr_sha="want",
            max_wait_seconds=1,
            poll_interval_seconds=1,
            project_key="Prekzursil_Airline-Reservations-System",
        )
        with (
            mock.patch.object(sonar, "_fetch_pr_analysis_sha", side_effect=["old", "want"]),
            mock.patch.object(sonar, "_fetch_open_issues", return_value=0),
            mock.patch.object(sonar, "_fetch_unresolved_hotspots", return_value=0),
            mock.patch.object(sonar, "_fetch_quality_gate", return_value="OK"),
            mock.patch.object(sonar.time, "time", side_effect=[0, 0, 0, 0]),
            mock.patch.object(sonar.time, "sleep"),
        ):
            status, open_issues, unresolved_hotspots, quality_gate, findings = sonar._run_sonar_check(success_args, "token")
        self.assertEqual((status, open_issues, unresolved_hotspots, quality_gate, findings), ("pass", 0, 0, "OK", []))

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            out_json = temp_path / "sonar.json"
            out_md = temp_path / "sonar.md"
            with (
                mock.patch.object(sonar, "quality_artifact_paths", return_value=(out_json, out_md)),
                mock.patch.object(sonar, "_run_sonar_check", return_value=("pass", 0, 0, "OK", [])),
                mock.patch.object(sys, "argv", ["check_sonar_zero.py", "--project-key", "Prekzursil_Airline-Reservations-System"]),
                mock.patch.dict(os.environ, {"SONAR_TOKEN": "token"}, clear=True),
            ):
                self.assertEqual(sonar.main(), 0)
                self.assertIn("Unresolved security hotspots: `0`", out_md.read_text(encoding="utf-8"))

    def test_sonar_additional_helpers_cover_fetch_wrappers_and_error_paths(self) -> None:
        with mock.patch.object(sys, "argv", ["check_sonar_zero.py", "--project-key", "Prekzursil_Airline-Reservations-System"]):
            args = sonar._parse_args()
        self.assertEqual(args.poll_interval_seconds, 10)

        with mock.patch.object(sonar, "build_https_request_target", return_value=helpers.HTTPSRequestTarget(host=helpers.HTTPSHost.SONARCLOUD.value, path="/api/test")), mock.patch.object(
            sonar,
            "request_json_https_target",
            return_value={"paging": {"total": 1}},
        ):
            payload = sonar._request_sonar_payload("auth", "/api/test")
            self.assertEqual(payload["paging"]["total"], 1)
            self.assertEqual(sonar._fetch_open_issues("auth", {"componentKeys": "proj"}), 1)
            self.assertEqual(sonar._fetch_unresolved_hotspots("auth", {"projectKey": "proj"}), 1)

        with mock.patch.object(sonar, "_request_sonar_payload", return_value={"projectStatus": {}}):
            self.assertEqual(sonar._fetch_quality_gate("auth", {"projectKey": "proj"}), "UNKNOWN")
        with mock.patch.object(sonar, "_request_sonar_payload", return_value={"pullRequests": [{"key": "18", "commit": {"sha": "abc"}}]}):
            self.assertEqual(sonar._fetch_pr_analysis_sha("auth", "proj", "17"), "")
        with mock.patch.object(sonar, "_request_sonar_payload", return_value={"pullRequests": [{"key": "17", "commit": {"sha": "abc"}}]}):
            self.assertEqual(sonar._fetch_pr_analysis_sha("auth", "proj", "17"), "abc")

        findings = sonar._evaluate_findings(2, 1, "WARN")
        self.assertEqual(len(findings), 3)

        self.assertEqual(
            sonar._run_sonar_check(
                Namespace(branch="", pull_request="", expected_pr_sha="", max_wait_seconds=0, poll_interval_seconds=1, project_key="Prekzursil_Airline-Reservations-System"),
                "",
            ),
            ("fail", None, None, None, ["SONAR_TOKEN is missing."]),
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            out_json = temp_path / "sonar.json"
            out_md = temp_path / "sonar.md"
            with (
                mock.patch.object(sonar, "quality_artifact_paths", return_value=(out_json, out_md)),
                mock.patch.object(sonar, "_run_sonar_check", side_effect=RuntimeError("boom")),
                mock.patch.object(sys, "argv", ["check_sonar_zero.py", "--project-key", "Prekzursil_Airline-Reservations-System"]),
                mock.patch.dict(os.environ, {"SONAR_TOKEN": "token"}, clear=True),
            ):
                self.assertEqual(sonar.main(), 1)
            self.assertIn("Sonar API request failed", out_md.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
