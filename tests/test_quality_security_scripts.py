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

from scripts import security_helpers as helpers
from scripts.quality import check_codacy_zero as codacy
from scripts.quality import check_deepscan_zero as deepscan
from scripts.quality import check_quality_secrets as quality_secrets
from scripts.quality import check_required_checks as required_checks
from scripts.quality import check_sentry_zero as sentry


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
    def test_quality_secrets_artifacts_exclude_present_secret_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            previous = Path.cwd()
            os.chdir(temp_dir)
            try:
                env_updates = {
                    "SONAR_TOKEN": "configured-sonar-token",
                    "CODECOV_TOKEN": "configured-codecov-token",
                    "SENTRY_ORG": "example-org",
                    "SENTRY_PROJECT": "example-project",
                }
                with mock.patch.dict(os.environ, env_updates, clear=False):
                    with mock.patch.object(sys, "argv", ["check_quality_secrets.py"]):
                        exit_code = quality_secrets.main()

                out_json, out_md = helpers.quality_artifact_paths(helpers.QualityArtifact.QUALITY_SECRETS)
                payload_text = out_json.read_text(encoding="utf-8")
                payload = json.loads(payload_text)
                markdown = out_md.read_text(encoding="utf-8")

                self.assertEqual(exit_code, 1)
                self.assertEqual(payload["status"], "fail")
                self.assertNotIn("missing_secrets", payload)
                self.assertNotIn("missing_vars", payload)
                self.assertEqual(payload["missing_secret_count"], 3)
                self.assertEqual(payload["missing_var_count"], 0)
                self.assertNotIn("required_secrets", payload)
                self.assertNotIn("required_vars", payload)
                self.assertNotIn("present_secrets", payload)
                self.assertNotIn("present_vars", payload)
                self.assertNotIn("configured-sonar-token", payload_text)
                self.assertNotIn("configured-codecov-token", payload_text)
                self.assertIn("Missing secrets", markdown)
                self.assertIn("Count: `3`", markdown)
                self.assertIn("Names omitted from artifacts", markdown)
                self.assertNotIn("configured-sonar-token", markdown)
                self.assertNotIn("configured-codecov-token", markdown)
                self.assertNotIn("SNYK_TOKEN", markdown)
                self.assertNotIn("SENTRY_AUTH_TOKEN", markdown)
            finally:
                os.chdir(previous)


if __name__ == "__main__":
    unittest.main()
