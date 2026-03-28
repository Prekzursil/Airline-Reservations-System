"""Main-flow coverage for Airline quality helper scripts."""

from __future__ import absolute_import, division

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import List
from unittest import TestCase, mock

from scripts import security_helpers as helpers
from scripts.quality import check_codacy_zero as codacy
from scripts.quality import check_deepscan_zero as deepscan
from scripts.quality import check_required_checks as required_checks
from scripts.quality import check_sentry_zero as sentry
from scripts.quality import check_sonar_zero as sonar


class QualityScriptArgParsingTests(TestCase):
    """Argument parsing regression checks for the quality helper scripts."""

    def test_codacy_parse_args_accepts_branch(self) -> None:
        with mock.patch.object(
            sys,
            "argv",
            [
                "prog",
                "--owner",
                "Prekzursil",
                "--repo",
                "Airline-Reservations-System",
                "--branch",
                "feature/test",
            ],
        ):
            args = codacy._parse_args()
        self.assertEqual(args.owner, "Prekzursil")
        self.assertEqual(args.repo, "Airline-Reservations-System")
        self.assertEqual(args.branch, "feature/test")

    def test_deepscan_parse_args_accepts_required_context(self) -> None:
        with mock.patch.object(
            sys,
            "argv",
            [
                "prog",
                "--repo",
                "Prekzursil/Airline-Reservations-System",
                "--sha",
                "a1b2c3d",
                "--required-context",
                "DeepScan",
            ],
        ):
            args = deepscan._parse_args()
        self.assertEqual(args.required_context, "DeepScan")

    def test_required_checks_parse_args_collects_contexts(self) -> None:
        with mock.patch.object(
            sys,
            "argv",
            [
                "prog",
                "--repo",
                "Prekzursil/Airline-Reservations-System",
                "--sha",
                "a1b2c3d",
                "--required-context",
                "verify",
                "--required-context",
                "SonarCloud",
            ],
        ):
            args = required_checks._parse_args()
        self.assertEqual(args.required_context, ["verify", "SonarCloud"])

    def test_sentry_parse_args_accepts_projects(self) -> None:
        with mock.patch.object(
            sys,
            "argv",
            ["prog", "--org", "my-org", "--project", "backend", "--project", "web"],
        ):
            args = sentry._parse_args()
        self.assertEqual(args.org, "my-org")
        self.assertEqual(args.project, ["backend", "web"])

    def test_sonar_parse_args_accepts_branch_and_pr(self) -> None:
        with mock.patch.object(
            sys,
            "argv",
            [
                "prog",
                "--project-key",
                "Prekzursil_Airline-Reservations-System",
                "--branch",
                "feature-x",
                "--pull-request",
                "30",
            ],
        ):
            args = sonar._parse_args()
        self.assertEqual(args.branch, "feature-x")
        self.assertEqual(args.pull_request, "30")


class QualityScriptMainFlowTests(TestCase):
    """Main-flow regression checks for quality helper scripts and artifact emission."""

    def test_codacy_run_check_fails_without_token(self) -> None:
        open_issues, findings, status = codacy._run_codacy_check(
            mock.Mock(provider="gh", owner="Prekzursil", repo="Airline-Reservations-System", branch=""),
            "",
        )
        self.assertIsNone(open_issues)
        self.assertEqual(status, "fail")
        self.assertIn("CODACY_API_TOKEN is missing.", findings)

    def test_codacy_evaluate_status_and_render_md_cover_empty_findings(self) -> None:
        findings: List[str] = []
        self.assertEqual(codacy._evaluate_status(0, findings), "pass")
        self.assertEqual(findings, [])

        payload = {
            "status": "pass",
            "owner": "Prekzursil",
            "repo": "Airline-Reservations-System",
            "branch": "",
            "open_issues": 0,
            "timestamp_utc": "2026-03-28T00:00:00+00:00",
            "findings": [],
        }
        rendered = codacy._render_md(payload)
        self.assertIn("- None", rendered)
        self.assertIn("`default`", rendered)

    def test_codacy_fetch_open_issues_without_branch_and_runtime_failure(self) -> None:
        args = mock.Mock(provider="gh", owner="Prekzursil", repo="Airline-Reservations-System", branch="")
        captured = {}

        def _fake_request_json_https_target(**kwargs):
            captured.update(kwargs)
            return {"total": 0}

        fixture_auth = "-".join(("fixture", "auth", "value"))
        with mock.patch.object(
            codacy,
            "request_json_https_target",
            side_effect=_fake_request_json_https_target,
        ):
            self.assertEqual(codacy._fetch_open_issues(args, fixture_auth), 0)

        self.assertEqual(captured["body"], {})

        with mock.patch.object(codacy, "_fetch_open_issues", side_effect=RuntimeError("boom")):
            open_issues, findings, status = codacy._run_codacy_check(
                args,
                fixture_auth,
            )
        self.assertIsNone(open_issues)
        self.assertEqual(status, "fail")
        self.assertIn("boom", findings[0])

    def test_deepscan_main_writes_outputs_with_stubbed_result(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            previous = Path.cwd()
            os.chdir(temp_dir)
            try:
                args = mock.Mock(repo="Prekzursil/Airline-Reservations-System", sha="a1b2c3d", required_context="DeepScan")
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

    def test_deepscan_helpers_cover_pending_and_render_paths(self) -> None:
        target = helpers.HTTPSRequestTarget(host=helpers.HTTPSHost.GITHUB_API.value, path="/repos/o/r/commits/a1b2c3d/status")

        fixture_auth = "-".join(("fixture", "auth", "value"))
        with mock.patch.object(
            deepscan,
            "request_json_https_target",
            return_value={"ok": True},
        ):
            self.assertEqual(deepscan._api_get(target, fixture_auth), {"ok": True})

        self.assertEqual(deepscan._poll_or_timeout(0, 1, 0), True)
        self.assertEqual(deepscan._poll_or_timeout(2, 1, 0), False)
        self.assertIn(
            "expected success",
            deepscan._pending_failure_message(
                "DeepScan",
                {"source": "status", "conclusion": ""},
            ),
        )
        self.assertTrue(deepscan._is_pending_context({"source": "status", "conclusion": ""}))
        self.assertEqual(
            deepscan._context_outcome(
                "DeepScan",
                {"source": "status", "conclusion": "failure"},
            )[0],
            "fail",
        )
        self.assertIn(
            "- None",
            deepscan._render_md(
                {
                    "status": "pass",
                    "repo": "r",
                    "sha": "a1",
                    "required_context": "DeepScan",
                    "timestamp_utc": "x",
                    "findings": [],
                }
            ),
        )

    def test_deepscan_run_check_covers_pending_and_failure_outcomes(self) -> None:
        args = mock.Mock(
            repo="Prekzursil/Airline-Reservations-System",
            sha="a1b2c3d",
            required_context="DeepScan",
            max_wait_seconds=0,
            poll_interval_seconds=0,
        )

        with mock.patch.object(
            deepscan,
            "_api_get",
            side_effect=[
                {"check_runs": [{"name": "DeepScan", "status": "completed", "conclusion": "failure"}]},
                {"statuses": []},
            ],
        ):
            status, findings, observed = deepscan._run_deepscan_check(
                args,
                "-".join(("fixture", "auth", "value")),
            )
        self.assertEqual(status, "fail")
        self.assertIn("expected success", findings[0])
        self.assertIsNotNone(observed)

        args_pending = mock.Mock(
            repo="Prekzursil/Airline-Reservations-System",
            sha="a1b2c3d",
            required_context="DeepScan",
            max_wait_seconds=0,
            poll_interval_seconds=0,
        )
        with mock.patch.object(
            deepscan,
            "_api_get",
            side_effect=[
                {"check_runs": [{"name": "DeepScan", "status": "in_progress", "conclusion": None}]},
                {"statuses": []},
            ],
        ):
            status, findings, _observed = deepscan._run_deepscan_check(
                args_pending,
                "-".join(("fixture", "auth", "value")),
            )
        self.assertEqual(status, "fail")
        self.assertIn("expected completed", findings[0])

    def test_required_checks_api_get_retries_then_succeeds(self) -> None:
        calls = {"count": 0}

        def _fake_request_json_https_target(**_kwargs):
            calls["count"] += 1
            if calls["count"] < 3:
                raise helpers.HTTPSRequestError(503, "Unavailable", "retry")
            return {"ok": True}

        with mock.patch.object(required_checks, "request_json_https_target", side_effect=_fake_request_json_https_target), mock.patch.object(
            required_checks.time, "sleep", lambda _seconds: None
        ):
            payload = required_checks._api_get(
                helpers.HTTPSRequestTarget(host=helpers.HTTPSHost.GITHUB_API.value, path="/repos/o/r/commits/a1b2c3d/status"),
                "-".join(("fixture", "auth", "value")),
            )

        self.assertEqual(payload, {"ok": True})
        self.assertEqual(calls["count"], 3)

    def test_required_checks_helpers_cover_render_and_token_validation(self) -> None:
        self.assertIn(
            "- None",
            required_checks._render_md(
                {
                    "status": "pass",
                    "repo": "r",
                    "sha": "a1",
                    "timestamp_utc": "x",
                    "missing": [],
                    "failed": [],
                }
            ),
        )
        target = helpers.HTTPSRequestTarget(host=helpers.HTTPSHost.GITHUB_API.value, path="/repos/o/r/commits/a1b2c3d/status")
        with mock.patch.object(
            required_checks,
            "request_json_https_target",
            side_effect=RuntimeError("transport"),
        ), mock.patch.object(required_checks.time, "sleep", lambda _seconds: None):
            with self.assertRaises(RuntimeError):
                required_checks._api_get(
                    target,
                    "-".join(("fixture", "auth", "value")),
                )

        args = mock.Mock(
            repo="Prekzursil/Airline-Reservations-System",
            sha="a1b2c3d",
            required_context=["verify"],
            timeout_seconds=1,
            poll_seconds=0,
        )
        with mock.patch.object(required_checks, "_parse_args", return_value=args), mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(SystemExit):
                required_checks.main()

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

    def test_sentry_main_handles_runtime_exception_and_writes_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            previous = Path.cwd()
            os.chdir(temp_dir)
            try:
                args = mock.Mock(
                    org="my-org",
                    project=["proj"],
                    token="-".join(("fixture", "token")),
                )
                with mock.patch.object(sentry, "_parse_args", return_value=args), mock.patch.object(
                    sentry,
                    "_run_sentry_check",
                    side_effect=RuntimeError("boom"),
                ):
                    rc = sentry.main()

                out_json, out_md = helpers.quality_artifact_paths(helpers.QualityArtifact.SENTRY_ZERO)
                payload = json.loads(out_json.read_text(encoding="utf-8"))
                self.assertEqual(rc, 1)
                self.assertEqual(payload["status"], "fail")
                self.assertIn("boom", payload["findings"][0])
                self.assertTrue(out_md.exists())
            finally:
                os.chdir(previous)

    def test_sentry_helpers_cover_validation_and_findings(self) -> None:
        self.assertEqual(
            sentry._validate_inputs("", "", []),
            [
                "SENTRY_AUTH_TOKEN is missing.",
                "SENTRY_ORG is missing.",
                "No Sentry projects configured.",
            ],
        )
        findings: list[str] = []
        self.assertEqual(sentry._unresolved_count("proj", [], {}, findings), 0)
        self.assertEqual(findings, [])
        findings = []
        sentry._append_project_fetch_failure("proj", None, "org", findings)
        self.assertIn("did not return data", findings[0])
        rendered = sentry._render_md(
            {
                "status": "pass",
                "org": "org",
                "timestamp_utc": "x",
                "projects": [],
                "findings": [],
            }
        )
        self.assertIn("- None", rendered)

    def test_sonar_main_writes_success_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            previous = Path.cwd()
            os.chdir(temp_dir)
            try:
                args = mock.Mock(
                    project_key="Prekzursil_Airline-Reservations-System",
                    token="-".join(("fixture", "token")),
                    branch="",
                    pull_request="",
                    expected_pr_sha="",
                )
                with mock.patch.object(sonar, "_parse_args", return_value=args), mock.patch.object(
                    sonar,
                    "_run_sonar_check",
                    return_value=("pass", 0, 0, "OK", []),
                ):
                    rc = sonar.main()

                out_json, out_md = helpers.quality_artifact_paths(helpers.QualityArtifact.SONAR_ZERO)
                payload = json.loads(out_json.read_text(encoding="utf-8"))
                self.assertEqual(rc, 0)
                self.assertEqual(payload["quality_gate"], "OK")
                self.assertTrue(out_md.exists())
            finally:
                os.chdir(previous)

    def test_sonar_helpers_cover_render_and_runtime_failure(self) -> None:
        payload = {
            "status": "pass",
            "project_key": "key",
            "open_issues": 0,
            "unresolved_security_hotspots": 0,
            "quality_gate": "OK",
            "timestamp_utc": "x",
            "findings": [],
        }
        self.assertIn("- None", sonar._render_md(payload))

        args = mock.Mock(
            project_key="Prekzursil_Airline-Reservations-System",
            token="-".join(("fixture", "token")),
            branch="",
            pull_request="",
            expected_pr_sha="",
        )
        with mock.patch.object(sonar, "_parse_args", return_value=args), mock.patch.object(
            sonar,
            "_run_sonar_check",
            side_effect=RuntimeError("boom"),
        ):
            rc = sonar.main()
        self.assertEqual(rc, 1)
