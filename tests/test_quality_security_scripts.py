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

_AUTH_TOKEN = "-".join(("fixture", "auth", "value"))

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
        merged = helpers._merge_safe_headers({"X-Test": _AUTH_TOKEN}, include_json_content_type=False)
        self.assertEqual(merged["Accept"], "application/json")
        self.assertEqual(merged["X-Test"], _AUTH_TOKEN)
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

        def _fake_request_json_https_target(*, target, method, headers, body):
            captured["target"] = target
            captured["method"] = method
            captured["headers"] = headers
            captured["body"] = body
            return {"total": 0}

        with mock.patch.object(codacy, "request_json_https_target", side_effect=_fake_request_json_https_target):
            self.assertEqual(codacy._fetch_open_issues(args, _AUTH_TOKEN), 0)

        self.assertEqual(captured["method"], "POST")
        self.assertEqual(captured["body"], {"branchName": "feature/zero"})

    def test_sentry_path_builder_rejects_invalid_project(self) -> None:
        path = sentry._build_project_issues_path("org-name", "project_name")
        self.assertTrue(path.startswith("/api/0/projects/org-name/project_name/issues/?"))

        with self.assertRaises(ValueError):
            sentry._build_project_issues_path("org-name", "../project")
        with self.assertRaises(ValueError):
            sentry._resolve_project_slug("org-name", "bad/project", _AUTH_TOKEN)

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

    def test_deepscan_context_helpers_cover_status_and_pending_paths(self) -> None:
        contexts = deepscan._collect_contexts(
            {"check_runs": [{"name": "DeepScan", "status": "in_progress", "conclusion": None}]},
            {"statuses": [{"context": "legacy", "state": "success"}]},
        )

        self.assertEqual(contexts["DeepScan"]["source"], "check_run")
        self.assertEqual(contexts["legacy"]["source"], "status")
        self.assertTrue(deepscan._is_pending_context(contexts["DeepScan"]))
        self.assertEqual(
            deepscan._context_outcome("legacy", contexts["legacy"]),
            ("pass", None),
        )
        self.assertIn(
            "expected success",
            deepscan._context_outcome("DeepScan", {"source": "check_run", "state": "completed", "conclusion": "failure"})[1],
        )

    def test_required_checks_helpers_cover_context_collection_and_failures(self) -> None:
        contexts = required_checks._collect_contexts(
            {"check_runs": [{"name": "verify", "status": "completed", "conclusion": "success"}]},
            {"statuses": [{"context": "DeepScan", "state": "failure"}]},
        )

        status, missing, failed = required_checks._evaluate(["verify", "DeepScan", "SonarCloud"], contexts)

        self.assertEqual(status, "fail")
        self.assertEqual(missing, ["SonarCloud"])
        self.assertEqual(failed, ["DeepScan: state=failure"])
        self.assertFalse(required_checks._has_check_runs_in_progress(contexts))

    def test_required_checks_collect_payload_converges_when_checks_pass(self) -> None:
        args = mock.Mock(repo="Prekzursil/Airline-Reservations-System", sha="a1b2c3d", timeout_seconds=1, poll_seconds=0)

        with mock.patch.object(
            required_checks,
            "_fetch_check_payloads",
            return_value=(
                {"check_runs": [{"name": "verify", "status": "completed", "conclusion": "success"}]},
                {"statuses": []},
            ),
        ):
            payload = required_checks._collect_payload(args, ["verify"], _AUTH_TOKEN)

        self.assertEqual(payload["status"], "pass")
        self.assertEqual(payload["missing"], [])
        self.assertEqual(payload["failed"], [])


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

    def test_sonar_run_check_handles_missing_token(self) -> None:
        args = mock.Mock(project_key="Prekzursil_Airline-Reservations-System", branch="", pull_request="", expected_pr_sha="")

        status, open_issues, unresolved_hotspots, quality_gate, findings = sonar._run_sonar_check(args, "")

        self.assertEqual(status, "fail")
        self.assertIsNone(open_issues)
        self.assertIsNone(unresolved_hotspots)
        self.assertIsNone(quality_gate)
        self.assertEqual(findings, ["SONAR_TOKEN is missing."])

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
                    "-".join(("fixture", "auth", "value")),
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


class CodacyAndSentryMainFlowTests(unittest.TestCase):
    def test_codacy_extract_total_open_handles_nested_and_missing_counts(self) -> None:
        payload = {"outer": [{"nested": {"open_issues": 7}}, {"other": "x"}]}
        self.assertEqual(codacy.extract_total_open(payload), 7)
        self.assertEqual(codacy.extract_total_open({"pagination": {"total": 4}}), 4)
        self.assertIsNone(codacy.extract_total_open({"outer": [{"nested": "value"}]}))

    def test_codacy_main_writes_outputs_without_token(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            previous = Path.cwd()
            os.chdir(temp_dir)
            try:
                args = mock.Mock(
                    provider="gh",
                    owner="Prekzursil",
                    repo="Airline-Reservations-System",
                    branch="",
                    token=str(),
                )
                with mock.patch.object(
                    codacy,
                    "_parse_args",
                    return_value=args,
                ), mock.patch.dict(os.environ, {}, clear=False):
                    rc = codacy.main()

                out_json, out_md = helpers.quality_artifact_paths(helpers.QualityArtifact.CODACY_ZERO)
                self.assertEqual(rc, 1)
                self.assertTrue(out_json.exists())
                self.assertTrue(out_md.exists())
            finally:
                os.chdir(previous)

    def test_sentry_helpers_cover_project_resolution(self) -> None:
        self.assertEqual(sentry._hits_from_headers({"x-hits": "2"}), 2)
        self.assertIsNone(sentry._hits_from_headers({"x-hits": "bad"}))
        self.assertEqual(
            sentry._projects_from_args_or_env(mock.Mock(project=["backend"])),
            ["backend"],
        )
        self.assertEqual(
            sentry._projects_from_args_or_env(mock.Mock(project=[])),
            [],
        )
        self.assertEqual(
            sentry._project_slug_from_match(
                {"slug": "backend-service", "name": "Backend Service"},
                "backend service",
            ),
            "backend-service",
        )

        with mock.patch.object(
            sentry,
            "_fetch_org_projects",
            return_value=[{"slug": "backend-service", "name": "Backend Service"}],
        ):
            candidates = sentry._project_candidates(
                "org",
                "Backend_Service",
                "-".join(("fixture", "auth", "value")),
            )

        self.assertIn("Backend_Service", candidates)
        self.assertIn("Backend-Service", candidates)

    def test_sentry_main_writes_pass_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            previous = Path.cwd()
            os.chdir(temp_dir)
            try:
                args = mock.Mock(
                    org="my-org",
                    project=["proj"],
                    token="-".join(("fixture", "auth", "value")),
                )
                with mock.patch.object(
                    sentry,
                    "_run_sentry_check",
                    return_value=("pass", "my-org", [{"project": "proj", "unresolved": 0, "status": "ok"}], []),
                ), mock.patch.object(sentry, "_parse_args", return_value=args):
                    rc = sentry.main()

                out_json, out_md = helpers.quality_artifact_paths(helpers.QualityArtifact.SENTRY_ZERO)
                payload = json.loads(out_json.read_text(encoding="utf-8"))
                markdown = out_md.read_text(encoding="utf-8")
                self.assertEqual(rc, 0)
                self.assertEqual(payload["status"], "pass")
                self.assertIn("`proj` unresolved=`0`", markdown)
            finally:
                os.chdir(previous)


class DeepScanMainFlowTests(unittest.TestCase):
    def test_run_deepscan_check_reports_missing_context(self) -> None:
        args = mock.Mock(
            repo="Prekzursil/Airline-Reservations-System",
            sha="a1b2c3d",
            required_context="DeepScan",
            max_wait_seconds=0,
            poll_interval_seconds=0,
        )

        with mock.patch.object(deepscan, "_api_get", return_value={"check_runs": [], "statuses": []}):
            status, findings, observed = deepscan._run_deepscan_check(
                args,
                "-".join(("fixture", "auth", "value")),
            )

        self.assertEqual(status, "fail")
        self.assertEqual(findings, ["Missing required context: DeepScan"])
        self.assertIsNone(observed)

    def test_deepscan_main_writes_outputs_with_stubbed_result(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            previous = Path.cwd()
            os.chdir(temp_dir)
            try:
                args = mock.Mock(
                    repo="Prekzursil/Airline-Reservations-System",
                    sha="a1b2c3d",
                    required_context="DeepScan",
                )
                with mock.patch.object(deepscan, "_parse_args", return_value=args), mock.patch.dict(
                    os.environ,
                    {"GITHUB_TOKEN": "-".join(("fixture", "auth", "value"))},
                    clear=False,
                ), mock.patch.object(
                    deepscan,
                    "_run_deepscan_check",
                    return_value=("pass", [], {"state": "completed", "conclusion": "success", "source": "check_run"}),
                ):
                    rc = deepscan.main()

                out_json, out_md = helpers.quality_artifact_paths(helpers.QualityArtifact.DEEPSCAN_ZERO)
                self.assertEqual(rc, 0)
                self.assertTrue(out_json.exists())
                self.assertTrue(out_md.exists())
            finally:
                os.chdir(previous)


class RequiredChecksMainFlowTests(unittest.TestCase):
    def test_required_checks_main_writes_outputs_with_stubbed_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            previous = Path.cwd()
            os.chdir(temp_dir)
            try:
                args = mock.Mock(repo="Prekzursil/Airline-Reservations-System", sha="a1b2c3d", required_context=["verify"])
                payload = {
                    "status": "pass",
                    "repo": args.repo,
                    "sha": args.sha,
                    "required": ["verify"],
                    "missing": [],
                    "failed": [],
                    "contexts": {},
                    "timestamp_utc": "2026-03-27T00:00:00+00:00",
                }
                with mock.patch.object(required_checks, "_parse_args", return_value=args), mock.patch.dict(
                    os.environ,
                    {"GITHUB_TOKEN": "-".join(("fixture", "auth", "value"))},
                    clear=False,
                ), mock.patch.object(required_checks, "_collect_payload", return_value=payload):
                    rc = required_checks.main()

                out_json, out_md = helpers.quality_artifact_paths(helpers.QualityArtifact.REQUIRED_CHECKS)
                self.assertEqual(rc, 0)
                self.assertTrue(out_json.exists())
                self.assertTrue(out_md.exists())
            finally:
                os.chdir(previous)


class AdditionalQualityHelperCoverageTests(unittest.TestCase):
    def test_quality_secrets_helpers_cover_parse_dedupe_presence_and_markdown(self) -> None:
        with mock.patch.object(
            sys,
            "argv",
            [
                "check_quality_secrets.py",
                "--required-secret",
                "SNYK_TOKEN",
                "--required-secret",
                "SNYK_TOKEN",
                "--required-var",
                "SENTRY_REGION",
            ],
        ):
            args = quality_secrets._parse_args()

        self.assertEqual(args.required_secret, ["SNYK_TOKEN", "SNYK_TOKEN"])
        self.assertEqual(args.required_var, ["SENTRY_REGION"])
        self.assertEqual(
            quality_secrets._dedupe(["", "SNYK_TOKEN", " SNYK_TOKEN ", "SENTRY_REGION"]),
            ["SNYK_TOKEN", "SENTRY_REGION"],
        )

        with mock.patch.dict(
            os.environ,
            {"SNYK_TOKEN": _configured_value("snyk"), "SENTRY_REGION": "eu"},
            clear=True,
        ):
            payload = quality_secrets.evaluate_env(
                ["SNYK_TOKEN", "SONAR_TOKEN"],
                ["SENTRY_REGION", "SENTRY_PROJECT"],
            )

        self.assertEqual(payload["missing_secrets"], ["SONAR_TOKEN"])
        self.assertEqual(payload["missing_vars"], ["SENTRY_PROJECT"])
        self.assertEqual(payload["present_secrets"], ["SNYK_TOKEN"])
        self.assertEqual(payload["present_vars"], ["SENTRY_REGION"])
        self.assertIn(
            "Artifacts intentionally omit secret-derived details.",
            quality_secrets._render_md(timestamp_utc="2026-03-28T00:00:00+00:00"),
        )

    def test_codacy_helpers_cover_token_resolution_and_evaluate_failures(self) -> None:
        with mock.patch.dict(os.environ, {"CODACY_API_TOKEN": f" {_AUTH_TOKEN} "}, clear=True):
            self.assertEqual(codacy._resolve_token(""), _AUTH_TOKEN)
        self.assertEqual(codacy._resolve_token(f" {_AUTH_TOKEN} "), _AUTH_TOKEN)

        findings: list[str] = []
        self.assertEqual(codacy._evaluate_status(None, findings), "fail")
        self.assertIn("parseable total issue count", findings[0])

        findings = []
        self.assertEqual(codacy._evaluate_status(2, findings), "fail")
        self.assertIn("2 open issues", findings[0])

    def test_sentry_helper_branches_cover_fetch_resolution_and_evaluation(self) -> None:
        self.assertEqual(sentry._auth_headers(_AUTH_TOKEN)["Authorization"], f"Bearer {_AUTH_TOKEN}")
        target = sentry._build_org_projects_target("org-name", "backend")
        self.assertTrue(target.path.startswith("/api/0/organizations/org-name/projects/?"))

        with mock.patch.object(
            sentry,
            "request_json_list_https_target",
            return_value=([{"slug": "backend-service", "name": "Backend Service"}], {"x-hits": "1"}),
        ):
            projects = sentry._fetch_org_projects("org-name", "backend", _AUTH_TOKEN)
        self.assertEqual(projects, [{"slug": "backend-service", "name": "Backend Service"}])

        with mock.patch.object(
            sentry,
            "request_json_list_https_target",
            side_effect=RuntimeError("boom"),
        ):
            self.assertIsNone(sentry._fetch_org_projects("org-name", "backend", _AUTH_TOKEN))

        self.assertIsNone(sentry._project_slug_from_match({}, "backend"))
        self.assertIsNone(
            sentry._project_slug_from_match(
                {"slug": "backend-service", "name": "Backend Service"},
                "frontend",
            )
        )

        with mock.patch.object(sentry, "_fetch_org_projects", return_value=[]):
            self.assertIsNone(sentry._resolve_project_slug("org-name", "backend", _AUTH_TOKEN))

        with mock.patch.object(
            sentry,
            "_project_candidates",
            return_value=["missing", "backend-service"],
        ), mock.patch.object(
            sentry,
            "_fetch_project_issues",
            side_effect=[RuntimeError("404 Not Found"), ([{"id": 1}], {"x-hits": "1"})],
        ):
            resolved, issues, headers, error = sentry._select_project_payload(
                "org-name",
                "Backend_Service",
                _AUTH_TOKEN,
            )
        self.assertEqual(resolved, "backend-service")
        self.assertEqual(issues, [{"id": 1}])
        self.assertEqual(headers, {"x-hits": "1"})
        self.assertIsNone(error)

        not_found = RuntimeError("404 Not Found")
        other_error = RuntimeError("boom")
        with mock.patch.object(
            sentry,
            "_select_project_payload",
            side_effect=[
                (None, None, {}, not_found),
                (None, None, {}, other_error),
            ],
        ):
            project_results, findings = sentry._evaluate_projects(
                "org-name",
                ["missing", "broken"],
                _AUTH_TOKEN,
            )
        self.assertEqual(project_results[0]["status"], "not_found")
        self.assertIn("request failed", findings[0])
        self.assertTrue(sentry._is_not_found_error(not_found))
        self.assertFalse(sentry._is_not_found_error(other_error))

    def test_sonar_helper_branches_cover_fetchers_and_timeout(self) -> None:
        auth = sonar._auth_header(_AUTH_TOKEN)
        self.assertTrue(auth.startswith("Basic "))

        def _fake_request_json_https_target(*, target, method, headers):
            self.assertEqual(method, "GET")
            self.assertEqual(headers["Authorization"], auth)
            if target.path.startswith("/api/issues/search?"):
                return {"paging": {"total": 2}}
            if target.path.startswith("/api/qualitygates/project_status?"):
                return {"projectStatus": {"status": "ERROR"}}
            if target.path.startswith("/api/hotspots/search?"):
                return {"paging": {"total": 3}}
            if target.path.startswith("/api/project_pull_requests/list?"):
                return {"pullRequests": [{"key": "30", "commit": {"sha": "abc123"}}]}
            raise AssertionError(target.path)

        with mock.patch.object(
            sonar,
            "request_json_https_target",
            side_effect=_fake_request_json_https_target,
        ):
            self.assertEqual(
                sonar._fetch_open_issues(auth, {"componentKeys": "proj"}),
                2,
            )
            self.assertEqual(
                sonar._fetch_quality_gate(auth, {"projectKey": "proj"}),
                "ERROR",
            )
            self.assertEqual(
                sonar._fetch_unresolved_hotspots(auth, {"projectKey": "proj"}),
                3,
            )
            self.assertEqual(
                sonar._fetch_pr_analysis_sha(auth, "proj", "30"),
                "abc123",
            )
            self.assertEqual(sonar._fetch_pr_analysis_sha(auth, "proj", "31"), "")

        timeout_args = mock.Mock(
            project_key="Prekzursil_Airline-Reservations-System",
            branch="",
            pull_request="30",
            expected_pr_sha="expected",
            max_wait_seconds=0,
            poll_interval_seconds=0,
        )
        with mock.patch.object(sonar, "_fetch_pr_analysis_sha", return_value="stale"), mock.patch.object(
            sonar.time,
            "time",
            side_effect=[0, 0],
        ):
            status, open_issues, unresolved_hotspots, quality_gate, findings = sonar._run_sonar_check(
                timeout_args,
                _AUTH_TOKEN,
            )
        self.assertEqual(status, "fail")
        self.assertIsNone(open_issues)
        self.assertIsNone(unresolved_hotspots)
        self.assertIsNone(quality_gate)
        self.assertIn("Expected SHA: expected", findings)

    def test_required_checks_helper_branches_cover_error_and_main_guardrails(self) -> None:
        target = helpers.HTTPSRequestTarget(
            host=helpers.HTTPSHost.GITHUB_API.value,
            path="/repos/o/r/commits/a1b2c3d/status",
        )

        with mock.patch.object(
            required_checks,
            "request_json_https_target",
            side_effect=helpers.HTTPSRequestError(400, "Bad Request", "body"),
        ):
            with self.assertRaisesRegex(RuntimeError, "HTTP 400"):
                required_checks._api_get(target, _AUTH_TOKEN)

        with mock.patch.object(
            required_checks,
            "request_json_https_target",
            side_effect=[RuntimeError("boom")] * 4,
        ), mock.patch.object(required_checks.time, "sleep", lambda _seconds: None):
            with self.assertRaisesRegex(RuntimeError, "GitHub API request failed: boom"):
                required_checks._api_get(target, _AUTH_TOKEN)

        contexts: dict[str, dict[str, str]] = {}
        required_checks._collect_source_contexts(
            contexts,
            [None, {"name": "", "status": "completed", "conclusion": "success"}, {"name": "verify", "status": "queued", "conclusion": ""}],
            name_field="name",
            state_field="status",
            conclusion_field="conclusion",
            source="check_run",
        )
        self.assertEqual(
            required_checks._evaluate_check_run("verify", contexts["verify"]),
            "verify: status=queued",
        )
        self.assertEqual(
            required_checks._evaluate_status_context("DeepScan", {"conclusion": "pending"}),
            "DeepScan: state=pending",
        )

        args = mock.Mock(repo="Prekzursil/Airline-Reservations-System", sha="a1b2c3d", required_context=[], timeout_seconds=1, poll_seconds=0)
        with mock.patch.object(required_checks, "_parse_args", return_value=args), mock.patch.dict(
            os.environ,
            {"GITHUB_TOKEN": _AUTH_TOKEN},
            clear=True,
        ):
            with self.assertRaises(SystemExit):
                required_checks.main()

        args = mock.Mock(repo="Prekzursil/Airline-Reservations-System", sha="a1b2c3d", required_context=["verify"], timeout_seconds=1, poll_seconds=0)
        with mock.patch.object(required_checks, "_parse_args", return_value=args), mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(SystemExit):
                required_checks.main()

    def test_deepscan_helpers_cover_parse_fetch_and_main_guardrail(self) -> None:
        with mock.patch.object(
            sys,
            "argv",
            [
                "check_deepscan_zero.py",
                "--repo",
                "Prekzursil/Airline-Reservations-System",
                "--sha",
                "a1b2c3d",
            ],
        ):
            args = deepscan._parse_args()
        self.assertEqual(args.required_context, "DeepScan")

        target = deepscan._build_commit_api_target(
            "Prekzursil/Airline-Reservations-System",
            "a1b2c3d",
            "/status",
        )
        with mock.patch.object(
            deepscan,
            "request_json_https_target",
            return_value={"statuses": []},
        ):
            payload = deepscan._api_get(target, _AUTH_TOKEN)
        self.assertEqual(payload, {"statuses": []})

        args = mock.Mock(
            repo="Prekzursil/Airline-Reservations-System",
            sha="a1b2c3d",
            required_context="DeepScan",
            max_wait_seconds=0,
            poll_interval_seconds=0,
        )
        with mock.patch.object(deepscan, "_parse_args", return_value=args), mock.patch.dict(
            os.environ,
            {},
            clear=True,
        ):
            with self.assertRaises(SystemExit):
                deepscan.main()

    def test_sentry_helpers_cover_fetch_project_issues_and_run_check_success(self) -> None:
        with mock.patch.object(
            sentry,
            "request_json_list_https_target",
            return_value=([{"id": 1}], {"x-hits": "1"}),
        ):
            issues, headers = sentry._fetch_project_issues("org-name", "backend", _AUTH_TOKEN)
        self.assertEqual(issues, [{"id": 1}])
        self.assertEqual(headers, {"x-hits": "1"})

        args = mock.Mock(org="org-name", project=["backend"], token=_AUTH_TOKEN)
        with mock.patch.object(
            sentry,
            "_evaluate_projects",
            return_value=([{"project": "backend", "unresolved": 0, "status": "ok"}], []),
        ):
            status, org, project_results, findings = sentry._run_sentry_check(args)
        self.assertEqual(status, "pass")
        self.assertEqual(org, "org-name")
        self.assertEqual(project_results[0]["project"], "backend")
        self.assertEqual(findings, [])

    def test_sonar_helpers_cover_fetchers_and_success_path(self) -> None:
        def _fake_request_json_https_target(*, target, method, headers):
            self.assertEqual(method, "GET")
            self.assertEqual(headers["Authorization"], sonar._auth_header(_AUTH_TOKEN))
            if target.path.startswith("/api/issues/search?"):
                return {"paging": {"total": 0}}
            if target.path.startswith("/api/qualitygates/project_status?"):
                return {"projectStatus": {"status": "OK"}}
            if target.path.startswith("/api/hotspots/search?"):
                return {"paging": {"total": 0}}
            if target.path.startswith("/api/project_pull_requests/list?"):
                return {"pullRequests": [{"key": "30", "commit": {"sha": "expected"}}]}
            raise AssertionError(target.path)

        args = mock.Mock(
            project_key="Prekzursil_Airline-Reservations-System",
            branch="feature-x",
            pull_request="30",
            expected_pr_sha="expected",
            max_wait_seconds=0,
            poll_interval_seconds=0,
        )
        with mock.patch.object(
            sonar,
            "request_json_https_target",
            side_effect=_fake_request_json_https_target,
        ):
            status, open_issues, unresolved_hotspots, quality_gate, findings = sonar._run_sonar_check(
                args,
                _AUTH_TOKEN,
            )
        self.assertEqual(status, "pass")
        self.assertEqual(open_issues, 0)
        self.assertEqual(unresolved_hotspots, 0)
        self.assertEqual(quality_gate, "OK")
        self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()
