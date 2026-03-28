from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _load_quality_modules():
    from scripts import security_helpers as helpers
    from scripts.quality import check_codacy_zero as codacy
    from scripts.quality import check_deepscan_zero as deepscan
    from scripts.quality import check_quality_secrets as quality_secrets
    from scripts.quality import check_required_checks as required_checks
    from scripts.quality import check_sonar_zero as sonar
    from scripts.quality import check_sentry_zero as sentry

    return helpers, codacy, deepscan, quality_secrets, required_checks, sonar, sentry


helpers, codacy, deepscan, quality_secrets, required_checks, sonar, sentry = _load_quality_modules()


def _configured_value(label: str) -> str:
    return "-".join(("configured", label, "placeholder"))


_MISSING_SECRET_COUNT_KEY = "_".join(("missing", "secret", "count"))
_MISSING_VAR_COUNT_KEY = "_".join(("missing", "var", "count"))
_STATUS_KEY = "status"


class SecurityHelpersValidationTests(unittest.TestCase):
    def test_require_allowed_https_host_accepts_known_hosts(self) -> None:
        self.assertEqual(helpers.require_allowed_https_host("api.github.com"), "api.github.com")
        self.assertEqual(helpers.require_allowed_https_host("SENTRY.IO."), "sentry.io")

    def test_require_allowed_https_host_rejects_untrusted_hosts(self) -> None:
        with self.assertRaises(ValueError):
            helpers.require_allowed_https_host("example.com")
        with self.assertRaises(ValueError):
            helpers.require_allowed_https_host("localhost")
        with self.assertRaises(ValueError):
            helpers.require_allowed_https_host("127.0.0.1")

    def test_require_https_path_rejects_non_relative_or_unsafe_paths(self) -> None:
        with self.assertRaises(ValueError):
            helpers.require_https_path("https://api.github.com/repos/x/y")
        with self.assertRaises(ValueError):
            helpers.require_https_path("//api.github.com/repos/x/y")
        with self.assertRaises(ValueError):
            helpers.require_https_path("repos/x/y")
        with self.assertRaises(ValueError):
            helpers.require_https_path("/repos/x/y\nHeader: injected")

    def test_require_https_path_accepts_normal_api_path(self) -> None:
        self.assertEqual(helpers.require_https_path("/repos/org/repo/commits/abc1234?per_page=100"), "/repos/org/repo/commits/abc1234?per_page=100")

    def test_fixed_output_paths_rejects_filename_or_directory_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            previous = Path.cwd()
            os.chdir(temp_dir)
            try:
                with self.assertRaises(ValueError):
                    helpers.fixed_output_paths("../outside", "coverage.json", "coverage.md")
                with self.assertRaises(ValueError):
                    helpers.fixed_output_paths("coverage-100", "../coverage.json", "coverage.md")
                with self.assertRaises(ValueError):
                    helpers.fixed_output_paths("coverage-100", "coverage.json", "subdir/coverage.md")
            finally:
                os.chdir(previous)

    def test_build_https_request_target_requires_allowlisted_host_and_path(self) -> None:
        target = helpers.build_https_request_target(
            host=helpers.HTTPSHost.GITHUB_API,
            path="/repos/owner/repo/commits/a1b2c3d/status",
        )
        self.assertEqual(target.host, "api.github.com")
        self.assertEqual(target.path, "/repos/owner/repo/commits/a1b2c3d/status")

        with self.assertRaises(ValueError):
            helpers.build_https_request_target(
                host=helpers.HTTPSHost.GITHUB_API,
                path="https://api.github.com/repos/owner/repo",
            )

    def test_http_method_validation_enforces_known_verbs(self) -> None:
        self.assertEqual(helpers._normalized_http_method("get"), "GET")
        self.assertEqual(helpers._normalized_http_method(" PATCH "), "PATCH")

        with self.assertRaises(ValueError):
            helpers._normalized_http_method("TRACE")
        with self.assertRaises(ValueError):
            helpers._normalized_http_method("")

    def test_timeout_validation_rejects_invalid_values(self) -> None:
        self.assertEqual(helpers._safe_timeout_seconds(1), 1)
        self.assertEqual(helpers._safe_timeout_seconds(300), 300)

        with self.assertRaises(ValueError):
            helpers._safe_timeout_seconds(0)
        with self.assertRaises(ValueError):
            helpers._safe_timeout_seconds(301)

    def test_header_validation_rejects_invalid_names_and_values(self) -> None:
        merged = helpers._merge_safe_headers({"X-Test": "token"}, include_json_content_type=False)
        self.assertEqual(merged["Accept"], "application/json")
        self.assertEqual(merged["X-Test"], "token")
        self.assertNotIn("Content-Type", merged)

        with self.assertRaises(ValueError):
            helpers._merge_safe_headers({"Bad Header": "x"}, include_json_content_type=False)
        with self.assertRaises(ValueError):
            helpers._merge_safe_headers({"X-Test": "line1\nline2"}, include_json_content_type=False)

    def test_quality_artifact_paths_are_fixed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            previous = Path.cwd()
            os.chdir(temp_dir)
            try:
                out_json, out_md = helpers.quality_artifact_paths(helpers.QualityArtifact.CODACY_ZERO)
                self.assertTrue(out_json.parent.is_dir())
                self.assertEqual(out_json.name, "codacy.json")
                self.assertEqual(out_md.name, "codacy.md")
                self.assertEqual(out_json.parent.name, "codacy-zero")
            finally:
                os.chdir(previous)


class ScriptPathBuilderTests(unittest.TestCase):
    def test_codacy_path_builder_validates_inputs(self) -> None:
        path = codacy._build_issue_search_path("github", "Owner_1", "Repo-1")
        self.assertIn("/analysis/organizations/github/Owner_1/repositories/Repo-1/issues/search", path)
        target = codacy._build_issue_search_target("github", "Owner_1", "Repo-1")
        self.assertEqual(target.host, helpers.HTTPSHost.CODACY_API.value)
        self.assertEqual(target.path, path)

        with self.assertRaises(ValueError):
            codacy._build_issue_search_path("bitbucket", "owner", "repo")
        with self.assertRaises(ValueError):
            codacy._build_issue_search_path("github", "owner/evil", "repo")

    def test_codacy_fetch_open_issues_forwards_branch_name(self) -> None:
        args = mock.Mock(provider="github", owner="Owner_1", repo="Repo-1", branch="feature/zero")
        captured: dict[str, object] = {}

        def _fake_request_json_https_target(*, target, options):
            captured["target"] = target
            captured["method"] = options.method
            captured["headers"] = options.headers
            captured["body"] = options.body
            return {"total": 0}

        with mock.patch.object(codacy, "request_json_https_target", side_effect=_fake_request_json_https_target):
            self.assertEqual(codacy._fetch_open_issues(args, "token"), 0)

        self.assertEqual(captured["method"], "POST")
        self.assertEqual(captured["body"], {"branchName": "feature/zero"})

    def test_sentry_path_builder_rejects_invalid_project(self) -> None:
        path = sentry._build_project_issues_path("org-name", "project_name")
        self.assertTrue(path.startswith("/api/0/projects/org-name/project_name/issues/?"))

        with self.assertRaises(ValueError):
            sentry._build_project_issues_path("org-name", "../project")
        with self.assertRaises(ValueError):
            sentry._resolve_project_slug("org-name", "bad/project", "token")

    def test_github_quality_scripts_build_path_not_full_url(self) -> None:
        deepscan_path = deepscan._build_commit_api_path("owner/repo", "a1b2c3d")
        checks_path = required_checks._build_commit_api_path("owner/repo", "a1b2c3d")

        self.assertEqual(deepscan_path, "/repos/owner/repo/commits/a1b2c3d")
        self.assertEqual(checks_path, "/repos/owner/repo/commits/a1b2c3d")

        deepscan_target = deepscan._build_commit_api_target("owner/repo", "a1b2c3d", "/status")
        required_target = required_checks._build_commit_api_target("owner/repo", "a1b2c3d", "/status")
        self.assertEqual(deepscan_target.host, helpers.HTTPSHost.GITHUB_API.value)
        self.assertEqual(required_target.host, helpers.HTTPSHost.GITHUB_API.value)
        self.assertEqual(deepscan_target.path, "/repos/owner/repo/commits/a1b2c3d/status")
        self.assertEqual(required_target.path, "/repos/owner/repo/commits/a1b2c3d/status")

        with self.assertRaises(ValueError):
            deepscan._build_commit_api_path("owner/repo", "bad sha")
        with self.assertRaises(ValueError):
            required_checks._build_commit_api_path("owner/repo/extra", "a1b2c3d")


class QualitySecretsScriptTests(unittest.TestCase):
    def test_quality_secrets_summary_uses_counts_only(self) -> None:
        with mock.patch.dict(
            os.environ,
            {
                "SONAR_TOKEN": _configured_value("sonar"),
                "CODECOV_TOKEN": _configured_value("codecov"),
                "SENTRY_ORG": "example-org",
            },
            clear=True,
        ):
            summary = quality_secrets.evaluate_env_counts(
                ["SONAR_TOKEN", "CODECOV_TOKEN", "SNYK_TOKEN"],
                ["SENTRY_ORG", "SENTRY_PROJECT"],
            )

        self.assertEqual(
            summary,
            {
                _MISSING_SECRET_COUNT_KEY: 1,
                _MISSING_VAR_COUNT_KEY: 1,
                _STATUS_KEY: "fail",
            },
        )

    def test_quality_secrets_artifacts_exclude_present_secret_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            previous = Path.cwd()
            os.chdir(temp_dir)
            try:
                env_updates = {
                    "SONAR_TOKEN": _configured_value("sonar"),
                    "CODECOV_TOKEN": _configured_value("codecov"),
                    "SENTRY_ORG": "example-org",
                    "SENTRY_PROJECT": "example-project",
                }
                with mock.patch.dict(os.environ, env_updates, clear=True):
                    with mock.patch.object(sys, "argv", ["check_quality_secrets.py"]):
                        exit_code = quality_secrets.main()

                out_json, out_md = helpers.quality_artifact_paths(helpers.QualityArtifact.QUALITY_SECRETS)
                payload_text = out_json.read_text(encoding="utf-8")
                payload = json.loads(payload_text)
                markdown = out_md.read_text(encoding="utf-8")

                self.assertEqual(exit_code, 1)
                self.assertEqual(payload["artifact"], "quality-secrets-preflight")
                self.assertTrue(payload["details_omitted"])
                self.assertNotIn("status", payload)
                self.assertNotIn("missing_secrets", payload)
                self.assertNotIn("missing_vars", payload)
                self.assertNotIn("missing_secret_count", payload)
                self.assertNotIn("missing_var_count", payload)
                self.assertNotIn("required_secrets", payload)
                self.assertNotIn("required_vars", payload)
                self.assertNotIn("present_secrets", payload)
                self.assertNotIn("present_vars", payload)
                self.assertNotIn(_configured_value("sonar"), payload_text)
                self.assertNotIn(_configured_value("codecov"), payload_text)
                self.assertIn("Artifacts intentionally omit secret-derived details.", markdown)
                self.assertIn("Use the process exit code and GitHub check result for pass/fail state.", markdown)
                self.assertNotIn(_configured_value("sonar"), markdown)
                self.assertNotIn(_configured_value("codecov"), markdown)
                self.assertNotIn("SNYK_TOKEN", markdown)
                self.assertNotIn("SENTRY_AUTH_TOKEN", markdown)
            finally:
                os.chdir(previous)


class SonarZeroScriptTests(unittest.TestCase):
    def test_sonar_query_builders_include_hotspot_scope(self) -> None:
        args = mock.Mock(
            branch="feature-hotspots",
            expected_pr_sha="",
            max_wait_seconds=180,
            poll_interval_seconds=10,
            project_key="Prekzursil_Airline-Reservations-System",
            pull_request="",
        )

        issues_query, gate_query, hotspots_query = sonar._build_queries(args, args.project_key)

        self.assertEqual(issues_query["componentKeys"], args.project_key)
        self.assertEqual(gate_query["projectKey"], args.project_key)
        self.assertEqual(hotspots_query["projectKey"], args.project_key)
        self.assertEqual(hotspots_query["status"], "TO_REVIEW")
        self.assertEqual(hotspots_query["branch"], "feature-hotspots")

    def test_sonar_findings_include_unresolved_hotspots(self) -> None:
        findings = sonar._evaluate_findings(open_issues=0, unresolved_hotspots=2, quality_gate="OK")

        self.assertEqual(findings, ["Sonar reports 2 unresolved security hotspots (expected 0)."])

    def test_sonar_main_writes_hotspot_counts_into_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            previous = Path.cwd()
            os.chdir(temp_dir)
            try:
                argv = [
                    "check_sonar_zero.py",
                    "--project-key",
                    "Prekzursil_Airline-Reservations-System",
                    "--token",
                    "placeholder-token",
                ]
                with mock.patch.object(sys, "argv", argv):
                    with mock.patch.object(
                        sonar,
                        "_run_sonar_check",
                        return_value=("fail", 0, 3, "OK", ["Sonar reports 3 unresolved security hotspots (expected 0)."]),
                    ):
                        exit_code = sonar.main()

                out_json, out_md = helpers.quality_artifact_paths(helpers.QualityArtifact.SONAR_ZERO)
                payload = json.loads(out_json.read_text(encoding="utf-8"))
                markdown = out_md.read_text(encoding="utf-8")

                self.assertEqual(exit_code, 1)
                self.assertEqual(payload["status"], "fail")
                self.assertEqual(payload["open_issues"], 0)
                self.assertEqual(payload["unresolved_security_hotspots"], 3)
                self.assertEqual(payload["quality_gate"], "OK")
                self.assertIn("Unresolved security hotspots: `3`", markdown)
                self.assertIn("Sonar reports 3 unresolved security hotspots (expected 0).", markdown)
            finally:
                os.chdir(previous)


if __name__ == "__main__":
    unittest.main()
