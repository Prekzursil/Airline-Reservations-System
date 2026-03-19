from __future__ import absolute_import, division

import json
import os
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from typing import List
from unittest import mock

from scripts import security_helpers as helpers
from scripts.quality import check_deepscan_zero as deepscan
from scripts.quality import check_required_checks as required_checks
from scripts.quality import check_sentry_zero as sentry
from scripts.quality import check_sonar_zero as sonar
from scripts.quality import sentry_support
from scripts.quality import sentry_targets


def _join_parts(*parts: str) -> str:
    return "".join(parts)


REPO = "owner/repo"
SHA = "a1b2c3d"
DEEPSCAN_ARGV = ["check_deepscan_zero.py", "--repo", REPO, "--sha", SHA]
REQUIRED_CONTEXT = "Codecov Analytics"
REQUIRED_CHECKS_ARGV = [
    "check_required_checks.py",
    "--repo",
    REPO,
    "--sha",
    SHA,
    "--required-context",
    REQUIRED_CONTEXT,
]
SONAR_PROJECT_KEY = "Prekzursil_Airline-Reservations-System"


def _deepscan_args(**overrides):
    values = {
        "repo": REPO,
        "sha": SHA,
        "required_context": "DeepScan",
        "max_wait_seconds": 0,
        "poll_interval_seconds": 1,
    }
    values.update(overrides)
    return Namespace(**values)


def _required_checks_args(**overrides):
    values = {
        "repo": REPO,
        "sha": SHA,
        "timeout_seconds": 1,
        "poll_seconds": 1,
    }
    values.update(overrides)
    return Namespace(**values)


def _sonar_args(**overrides):
    values = {
        "branch": "feature",
        "pull_request": "17",
        "expected_pr_sha": "want",
        "max_wait_seconds": 0,
        "poll_interval_seconds": 1,
        "project_key": SONAR_PROJECT_KEY,
    }
    values.update(overrides)
    return Namespace(**values)


def _sentry_config():
    return sentry_targets.SentryConfig(
        org_label="Org",
        project_label="Project",
        user_agent="ua",
    )


class DeepScanAndRequiredChecksTests(unittest.TestCase):
    def test_deepscan_pending_and_context_helpers(self) -> None:
        self.assertEqual(
            deepscan._pending_failure_message(
                "DeepScan",
                {"source": "check_run", "state": "queued"},
            ),
            "DeepScan status is queued (expected completed)",
        )
        self.assertEqual(
            deepscan._pending_failure_message(
                "DeepScan",
                {"source": "status", "conclusion": "pending"},
            ),
            "DeepScan state is pending (expected success)",
        )
        self.assertTrue(
            deepscan._is_pending_context({"source": "check_run", "state": "in_progress"})
        )
        self.assertTrue(deepscan._is_pending_context({"source": "status", "conclusion": "pending"}))
        self.assertEqual(
            deepscan._context_outcome(
                "DeepScan",
                {
                    "source": "check_run",
                    "state": "completed",
                    "conclusion": "success",
                },
            ),
            ("pass", None),
        )
        self.assertEqual(
            deepscan._context_outcome(
                "DeepScan",
                {"source": "status", "conclusion": "failure"},
            ),
            ("fail", "DeepScan state is failure (expected success)"),
        )

    def test_run_deepscan_check_handles_missing_pending_and_success(self) -> None:
        args = _deepscan_args()
        with (
            mock.patch.object(deepscan, "_api_get", return_value={}),
            mock.patch.object(deepscan, "collect_contexts", return_value={}),
            mock.patch.object(deepscan, "_poll_or_timeout", return_value=False),
        ):
            status, findings, observed = deepscan._run_deepscan_check(args, "token")
        self.assertEqual((status, observed), ("fail", None))
        self.assertEqual(findings, ["Missing required context: DeepScan"])

        pending_context = {
            "DeepScan": {
                "source": "check_run",
                "state": "queued",
                "conclusion": "",
            }
        }
        with (
            mock.patch.object(deepscan, "_api_get", return_value={}),
            mock.patch.object(deepscan, "collect_contexts", return_value=pending_context),
            mock.patch.object(deepscan, "_poll_or_timeout", return_value=False),
        ):
            status, findings, observed = deepscan._run_deepscan_check(args, "token")
        self.assertEqual(status, "fail")
        self.assertEqual(observed, pending_context["DeepScan"])
        self.assertIn("expected completed", findings[0])

        success_context = {
            "DeepScan": {
                "source": "status",
                "state": "success",
                "conclusion": "success",
            }
        }
        with (
            mock.patch.object(deepscan, "_api_get", return_value={}),
            mock.patch.object(deepscan, "collect_contexts", return_value=success_context),
        ):
            status, findings, observed = deepscan._run_deepscan_check(args, "token")
        self.assertEqual(
            (status, findings, observed),
            ("pass", [], success_context["DeepScan"]),
        )

    def test_deepscan_parse_api_and_render_helpers(self) -> None:
        with mock.patch.object(sys, "argv", DEEPSCAN_ARGV):
            args = deepscan._parse_args()
        self.assertEqual(args.required_context, "DeepScan")

        target_payload = {"ok": True}
        with mock.patch.object(deepscan, "request_json_https_target", return_value=target_payload):
            self.assertEqual(
                deepscan._api_get(
                    helpers.HTTPSRequestTarget(
                        host="api.github.com",
                        path="/repos/owner/repo",
                    ),
                    "token",
                ),
                target_payload,
            )

        self.assertTrue(deepscan._poll_or_timeout(0, 1, 1))
        self.assertFalse(deepscan._poll_or_timeout(2, 1, 1))
        self.assertEqual(
            deepscan._context_outcome(
                "DeepScan",
                {
                    "source": "check_run",
                    "state": "completed",
                    "conclusion": "failure",
                },
            ),
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

    def test_deepscan_run_check_polling_paths(self) -> None:
        args = _deepscan_args(max_wait_seconds=1)
        pending_context = {
            "DeepScan": {
                "source": "status",
                "state": "pending",
                "conclusion": "pending",
            }
        }
        success_context = {
            "DeepScan": {
                "source": "status",
                "state": "success",
                "conclusion": "success",
            }
        }
        with (
            mock.patch.object(deepscan, "_api_get", return_value={}),
            mock.patch.object(
                deepscan,
                "collect_contexts",
                side_effect=[pending_context, success_context],
            ),
            mock.patch.object(deepscan, "_poll_or_timeout", side_effect=[True]),
        ):
            status, findings, observed = deepscan._run_deepscan_check(args, "token")
        self.assertEqual(
            (status, findings, observed),
            ("pass", [], success_context["DeepScan"]),
        )

        with (
            mock.patch.object(deepscan, "_api_get", return_value={}),
            mock.patch.object(deepscan, "collect_contexts", side_effect=[{}, {}]),
            mock.patch.object(deepscan, "_poll_or_timeout", side_effect=[True, False]),
        ):
            status, findings, observed = deepscan._run_deepscan_check(args, "token")
        self.assertEqual((status, observed), ("fail", None))
        self.assertEqual(findings, ["Missing required context: DeepScan"])

        failing_context = {
            "DeepScan": {
                "source": "status",
                "state": "failure",
                "conclusion": "failure",
            }
        }
        with (
            mock.patch.object(deepscan, "_api_get", return_value={}),
            mock.patch.object(deepscan, "collect_contexts", return_value=failing_context),
        ):
            status, findings, observed = deepscan._run_deepscan_check(args, "token")
        self.assertEqual((status, observed), ("fail", failing_context["DeepScan"]))
        self.assertIn("expected success", findings[0])

    def test_deepscan_main_failure_paths(self) -> None:
        with self.assertRaises(SystemExit):
            with mock.patch.object(sys, "argv", DEEPSCAN_ARGV):
                with mock.patch.dict(os.environ, {}, clear=True):
                    deepscan.main()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            out_json = temp_path / "deepscan.json"
            out_md = temp_path / "deepscan.md"
            with (
                mock.patch.object(
                    deepscan,
                    "quality_artifact_paths",
                    return_value=(out_json, out_md),
                ),
                mock.patch.object(
                    deepscan,
                    "_run_deepscan_check",
                    return_value=(
                        "fail",
                        ["broken"],
                        {"source": "status", "conclusion": "failure"},
                    ),
                ),
                mock.patch.object(sys, "argv", DEEPSCAN_ARGV),
                mock.patch.dict(os.environ, {"GITHUB_TOKEN": "token"}, clear=True),
            ):
                self.assertEqual(deepscan.main(), 1)
            payload = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "fail")
            self.assertIn("broken", out_md.read_text(encoding="utf-8"))

    def test_required_checks_api_retry_and_success_payload(self) -> None:
        response = {"ok": True}
        transient_error = helpers.HTTPSRequestError(503, "busy", "wait")
        with (
            mock.patch.object(
                required_checks,
                "request_json_https_target",
                side_effect=[transient_error, response],
            ),
            mock.patch.object(required_checks.time, "sleep") as sleep_mock,
        ):
            self.assertEqual(
                required_checks._api_get(
                    helpers.HTTPSRequestTarget(
                        host="api.github.com",
                        path="/repos/owner/repo",
                    ),
                    "token",
                ),
                response,
            )
        sleep_mock.assert_called_once()

        args = _required_checks_args()
        required = [REQUIRED_CONTEXT]
        with (
            mock.patch.object(required_checks, "_fetch_check_payloads", return_value=({}, {})),
            mock.patch.object(
                required_checks,
                "collect_contexts",
                return_value={
                    REQUIRED_CONTEXT: {
                        "source": "status",
                        "conclusion": "success",
                    }
                },
            ),
        ):
            payload = required_checks._collect_payload(args, required, "token")
        self.assertEqual(payload["status"], "pass")

    def test_required_checks_collect_payload_missing_context(self) -> None:
        args = _required_checks_args()
        required = [REQUIRED_CONTEXT]
        with (
            mock.patch.object(required_checks, "_fetch_check_payloads", return_value=({}, {})),
            mock.patch.object(required_checks, "collect_contexts", return_value={}),
            mock.patch.object(required_checks, "has_check_runs_in_progress", return_value=False),
            mock.patch.object(required_checks.time, "time", side_effect=[0, 0, 2]),
            mock.patch.object(required_checks.time, "sleep") as sleep_mock,
        ):
            payload = required_checks._collect_payload(args, required, "token")
        self.assertEqual(payload["status"], "fail")
        self.assertEqual(payload["missing"], [REQUIRED_CONTEXT])
        sleep_mock.assert_called_once_with(1)

    def test_required_checks_main_writes_pass_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            out_json = temp_path / "required.json"
            out_md = temp_path / "required.md"
            with (
                mock.patch.dict(os.environ, {"GITHUB_TOKEN": "token"}, clear=True),
                mock.patch.object(
                    required_checks,
                    "quality_artifact_paths",
                    return_value=(out_json, out_md),
                ),
                mock.patch.object(
                    required_checks,
                    "_collect_payload",
                    return_value={
                        "status": "pass",
                        "repo": REPO,
                        "sha": SHA,
                        "required": [REQUIRED_CONTEXT],
                        "missing": [],
                        "failed": [],
                        "contexts": {},
                        "timestamp_utc": "2026-03-19T00:00:00+00:00",
                    },
                ),
                mock.patch.object(sys, "argv", REQUIRED_CHECKS_ARGV),
            ):
                self.assertEqual(required_checks.main(), 0)
            self.assertIn("Status: `pass`", out_md.read_text(encoding="utf-8"))

    def test_required_checks_parse_api_error_and_render_helpers(self) -> None:
        with mock.patch.object(sys, "argv", REQUIRED_CHECKS_ARGV):
            args = required_checks._parse_args()
        self.assertEqual(args.timeout_seconds, 900)

        with (
            mock.patch.object(
                required_checks,
                "request_json_https_target",
                side_effect=[RuntimeError("boom")] * 4,
            ),
            mock.patch.object(required_checks.time, "sleep") as sleep_mock,
        ):
            with self.assertRaises(RuntimeError):
                required_checks._api_get(
                    helpers.HTTPSRequestTarget(
                        host="api.github.com",
                        path="/repos/owner/repo",
                    ),
                    "token",
                )
        self.assertEqual(sleep_mock.call_count, 3)
        with mock.patch.object(
            required_checks,
            "request_json_https_target",
            side_effect=helpers.HTTPSRequestError(404, "missing", "nope"),
        ):
            with self.assertRaises(RuntimeError):
                required_checks._api_get(
                    helpers.HTTPSRequestTarget(
                        host="api.github.com",
                        path="/repos/owner/repo",
                    ),
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
        self.assertIn(f"`{REQUIRED_CONTEXT}`", rendered)
        self.assertIn("QLTY Zero: conclusion=failure", rendered)

        with mock.patch.object(
            required_checks,
            "_api_get",
            side_effect=[{"check_runs": []}, {"statuses": []}],
        ):
            self.assertEqual(
                required_checks._fetch_check_payloads(REPO, SHA, "token"),
                ({"check_runs": []}, {"statuses": []}),
            )

    def test_required_checks_failure_and_input_paths(self) -> None:
        failing_args = _required_checks_args()
        with (
            mock.patch.object(required_checks, "_fetch_check_payloads", return_value=({}, {})),
            mock.patch.object(
                required_checks,
                "collect_contexts",
                return_value={
                    REQUIRED_CONTEXT: {
                        "source": "status",
                        "conclusion": "failure",
                    }
                },
            ),
            mock.patch.object(required_checks, "has_check_runs_in_progress", return_value=False),
            mock.patch.object(required_checks.time, "sleep") as sleep_mock,
        ):
            payload = required_checks._collect_payload(
                failing_args,
                [REQUIRED_CONTEXT],
                "token",
            )
        self.assertEqual(payload["failed"], [f"{REQUIRED_CONTEXT}: state=failure"])
        sleep_mock.assert_not_called()

        with (
            mock.patch.object(required_checks.time, "time", side_effect=[0, 2]),
            mock.patch.object(required_checks, "_fetch_check_payloads"),
        ):
            with self.assertRaises(RuntimeError):
                required_checks._collect_payload(
                    failing_args,
                    [REQUIRED_CONTEXT],
                    "token",
                )

        with self.assertRaises(SystemExit):
            with mock.patch.object(
                sys,
                "argv",
                ["check_required_checks.py", "--repo", REPO, "--sha", SHA],
            ):
                required_checks.main()
        with self.assertRaises(SystemExit):
            with mock.patch.object(sys, "argv", REQUIRED_CHECKS_ARGV):
                with mock.patch.dict(os.environ, {}, clear=True):
                    required_checks.main()


class SentryAndSonarScriptTests(unittest.TestCase):
    def test_sentry_target_helpers(self) -> None:
        config = _sentry_config()
        self.assertEqual(sentry_targets.hits_from_headers({"x-hits": "7"}), 7)
        self.assertIsNone(sentry_targets.hits_from_headers({"x-hits": "bad"}))
        self.assertEqual(
            sentry_targets.auth_headers("token", config)["Authorization"],
            "Bearer token",
        )
        self.assertIn(
            "query=is%3Aunresolved",
            sentry_targets.build_project_issues_path("org", "proj", config),
        )

        project_target = sentry_targets.build_project_issues_target("org", "proj", config)
        org_target = sentry_targets.build_org_projects_target("org", "proj", config)
        self.assertEqual(project_target.host, helpers.HTTPSHost.SENTRY.value)
        self.assertIn("/organizations/", org_target.path)

    def test_sentry_project_resolution_helpers(self) -> None:
        config = _sentry_config()
        self.assertEqual(
            sentry_support.project_slug_from_match(
                {"slug": "proj", "name": "Project"},
                "project",
            ),
            "proj",
        )
        self.assertIsNone(sentry_support.project_slug_from_match({"name": "Project"}, "project"))
        self.assertTrue(sentry_support.is_not_found_error(RuntimeError("404 Not Found")))
        self.assertIsNone(sentry_support.project_slug_from_match("bad", "proj"))
        self.assertIsNone(sentry_support.project_slug_from_match({"slug": ""}, "proj"))
        self.assertIsNone(
            sentry_support.project_slug_from_match(
                {"slug": "proj", "name": "Project"},
                "other",
            )
        )

        with mock.patch.object(
            sentry_support,
            "fetch_org_projects",
            return_value=[{"slug": "proj-backend", "name": "Backend"}],
        ):
            self.assertEqual(
                sentry_support.resolve_project_slug("org", "Backend", "token", config),
                "proj-backend",
            )

        with mock.patch.object(
            sentry_support,
            "resolve_project_slug",
            return_value="proj-backend",
        ):
            candidates = sentry_support.project_candidates(
                "org",
                "Proj_Backend",
                "token",
                config,
            )
        self.assertEqual(candidates[0], "proj-backend")
        self.assertIn("Proj_Backend", candidates)

        with mock.patch.object(sentry_support, "fetch_org_projects", return_value=None):
            self.assertIsNone(sentry_support.resolve_project_slug("org", "Proj", "token", config))
        with mock.patch.object(
            sentry_support,
            "fetch_org_projects",
            return_value=[{"slug": "proj", "name": "Project"}],
        ):
            self.assertIsNone(sentry_support.resolve_project_slug("org", "Other", "token", config))
        with mock.patch.object(sentry_support, "resolve_project_slug", return_value=None):
            self.assertEqual(
                sentry_support.project_candidates("org", "", "token", config),
                [],
            )

    def test_sentry_input_validation_and_failure_helpers(self) -> None:
        config = _sentry_config()
        with mock.patch.dict(
            os.environ,
            {"SENTRY_PROJECT_BACKEND": "backend", "SENTRY_PROJECT": "shared"},
            clear=True,
        ):
            self.assertEqual(
                sentry_support.projects_from_args_or_env(Namespace(project=[])),
                ["backend", "shared"],
            )

        self.assertEqual(
            sentry_support.validate_inputs("", "", []),
            [
                "SENTRY_AUTH_TOKEN is missing.",
                "SENTRY_ORG is missing.",
                "No Sentry projects configured.",
            ],
        )

        findings: List[str] = []
        unresolved = sentry_support.unresolved_count("proj", [{"id": 1}], {}, findings)
        self.assertEqual(unresolved, 1)
        self.assertIn("no X-Hits header", findings[0])

        findings = []
        sentry_support.append_project_fetch_failure(
            "proj",
            RuntimeError("404 Not Found"),
            "org",
            findings,
        )
        self.assertIn("not found in org", findings[0])

        findings = []
        sentry_support.append_project_fetch_failure("proj", None, "org", findings)
        self.assertIn("did not return data", findings[0])

        with mock.patch.dict(os.environ, {}, clear=True):
            status, org, project_results, findings = sentry_support.run_sentry_check(
                Namespace(org="", project=[], token=None),
                config,
            )
        self.assertEqual((status, org, project_results), ("fail", "", []))
        self.assertIn("SENTRY_AUTH_TOKEN is missing.", findings)

    def test_sentry_evaluation_and_run_check_helpers(self) -> None:
        config = _sentry_config()
        with mock.patch.object(
            sentry_support,
            "select_project_payload",
            side_effect=[
                ("proj", [], {"x-hits": "0"}, None),
                (None, None, {}, RuntimeError("404 Not Found")),
                (None, None, {}, RuntimeError("boom")),
            ],
        ):
            results, findings = sentry_support.evaluate_projects(
                "org",
                ["proj", "missing", "broken"],
                "token",
                config,
            )
        self.assertEqual(results[0]["status"], "ok")
        self.assertEqual(results[1]["status"], "not_found")
        self.assertIn("request failed", findings[-1])

        with mock.patch.object(
            sentry_support,
            "select_project_payload",
            return_value=("proj", [{"id": 1}], {"x-hits": "2"}, None),
        ):
            project_results, findings = sentry_support.evaluate_projects(
                "org",
                ["proj"],
                "token",
                config,
            )
        self.assertEqual(project_results[0]["unresolved"], 2)
        self.assertIn("expected 0", findings[0])

        sentry_token = _join_parts("tok", "en")
        args = Namespace(org="org", project=["proj"], token=sentry_token)
        with mock.patch.object(
            sentry_support,
            "evaluate_projects",
            return_value=(
                [
                    {
                        "project": "proj",
                        "resolved_project": "proj",
                        "unresolved": 0,
                        "status": "ok",
                    }
                ],
                [],
            ),
        ):
            status, org, project_results, findings = sentry_support.run_sentry_check(
                args,
                config,
            )
        self.assertEqual((status, org, findings), ("pass", "org", []))
        self.assertEqual(project_results[0]["project"], "proj")

    def test_sentry_parse_render_and_fetch_wrappers(self) -> None:
        config = _sentry_config()
        with mock.patch.object(
            sys,
            "argv",
            ["check_sentry_zero.py", "--org", "org", "--project", "proj"],
        ):
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

        with mock.patch.object(
            sentry_support,
            "request_json_list_https_target",
            return_value=([{"slug": "proj"}], {}),
        ):
            self.assertEqual(
                sentry_support.fetch_org_projects("org", "proj", "token", config),
                [{"slug": "proj"}],
            )
            self.assertEqual(
                sentry_support.fetch_project_issues("org", "proj", "token", config),
                ([{"slug": "proj"}], {}),
            )
        with mock.patch.object(
            sentry_support,
            "request_json_list_https_target",
            side_effect=RuntimeError("boom"),
        ):
            self.assertIsNone(sentry_support.fetch_org_projects("org", "proj", "token", config))

    def test_sentry_selection_and_main_failure_paths(self) -> None:
        config = _sentry_config()
        with (
            mock.patch.object(
                sentry_support,
                "project_candidates",
                return_value=["proj-a", "proj-b"],
            ),
            mock.patch.object(
                sentry_support,
                "fetch_project_issues",
                side_effect=[
                    RuntimeError("404 Not Found"),
                    ([{"id": 1}], {"x-hits": "1"}),
                ],
            ),
        ):
            resolved, issues, headers, last_error = sentry_support.select_project_payload(
                "org",
                "proj",
                "token",
                config,
            )
        self.assertEqual(
            (resolved, issues, headers, last_error),
            ("proj-b", [{"id": 1}], {"x-hits": "1"}, None),
        )

        with (
            mock.patch.object(
                sentry_support,
                "project_candidates",
                return_value=["proj-a", "proj-b"],
            ),
            mock.patch.object(
                sentry_support,
                "fetch_project_issues",
                side_effect=[
                    RuntimeError("404 Not Found"),
                    RuntimeError("404 Not Found"),
                ],
            ),
        ):
            resolved, issues, headers, last_error = sentry_support.select_project_payload(
                "org",
                "proj",
                "token",
                config,
            )
        self.assertEqual((resolved, issues, headers), (None, None, {}))
        self.assertIsInstance(last_error, RuntimeError)

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            out_json = temp_path / "sentry.json"
            out_md = temp_path / "sentry.md"
            with (
                mock.patch.object(
                    sentry,
                    "quality_artifact_paths",
                    return_value=(out_json, out_md),
                ),
                mock.patch.object(
                    sentry,
                    "run_sentry_check",
                    side_effect=ValueError("bad request"),
                ),
                mock.patch.object(sys, "argv", ["check_sentry_zero.py"]),
            ):
                self.assertEqual(sentry.main(), 1)
            self.assertIn(
                "Sentry API request failed",
                out_md.read_text(encoding="utf-8"),
            )

    def test_sonar_auth_and_timeout_findings(self) -> None:
        self.assertTrue(sonar._auth_header("token").startswith("Basic "))
        self.assertEqual(sonar._paged_total({"paging": {"total": 5}}), 5)

        args = _sonar_args(expected_pr_sha="want", max_wait_seconds=0)
        with (
            mock.patch.object(sonar, "_fetch_pr_analysis_sha", return_value="have"),
            mock.patch.object(sonar.time, "time", side_effect=[0, 1]),
        ):
            status, open_issues, unresolved_hotspots, quality_gate, findings = (
                sonar._run_sonar_check(args, "token")
            )
        self.assertEqual(status, "fail")
        self.assertIsNone(open_issues)
        self.assertIsNone(unresolved_hotspots)
        self.assertIsNone(quality_gate)
        self.assertIn("Expected SHA: want", findings)

    def test_sonar_success_and_main_success_path(self) -> None:
        success_args = _sonar_args(expected_pr_sha="want", max_wait_seconds=1)
        with (
            mock.patch.object(
                sonar,
                "_fetch_pr_analysis_sha",
                side_effect=["old", "want"],
            ),
            mock.patch.object(sonar, "_fetch_open_issues", return_value=0),
            mock.patch.object(sonar, "_fetch_unresolved_hotspots", return_value=0),
            mock.patch.object(sonar, "_fetch_quality_gate", return_value="OK"),
            mock.patch.object(sonar.time, "time", side_effect=[0, 0, 0, 0]),
            mock.patch.object(sonar.time, "sleep"),
        ):
            status, open_issues, unresolved_hotspots, quality_gate, findings = (
                sonar._run_sonar_check(success_args, "token")
            )
        self.assertEqual(
            (status, open_issues, unresolved_hotspots, quality_gate, findings),
            ("pass", 0, 0, "OK", []),
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            out_json = temp_path / "sonar.json"
            out_md = temp_path / "sonar.md"
            with (
                mock.patch.object(
                    sonar,
                    "quality_artifact_paths",
                    return_value=(out_json, out_md),
                ),
                mock.patch.object(
                    sonar,
                    "_run_sonar_check",
                    return_value=("pass", 0, 0, "OK", []),
                ),
                mock.patch.object(
                    sys,
                    "argv",
                    ["check_sonar_zero.py", "--project-key", SONAR_PROJECT_KEY],
                ),
                mock.patch.dict(os.environ, {"SONAR_TOKEN": "token"}, clear=True),
            ):
                self.assertEqual(sonar.main(), 0)
                self.assertIn(
                    "Unresolved security hotspots: `0`",
                    out_md.read_text(encoding="utf-8"),
                )

    def test_sonar_parse_request_and_fetch_wrappers(self) -> None:
        with mock.patch.object(
            sys,
            "argv",
            ["check_sonar_zero.py", "--project-key", SONAR_PROJECT_KEY],
        ):
            args = sonar._parse_args()
        self.assertEqual(args.poll_interval_seconds, 10)

        request_target = helpers.HTTPSRequestTarget(
            host=helpers.HTTPSHost.SONARCLOUD.value,
            path="/api/test",
        )
        with (
            mock.patch.object(
                sonar,
                "build_https_request_target",
                return_value=request_target,
            ),
            mock.patch.object(
                sonar,
                "request_json_https_target",
                return_value={"paging": {"total": 1}},
            ),
        ):
            payload = sonar._request_sonar_payload("auth", "/api/test")
            self.assertEqual(payload["paging"]["total"], 1)
            self.assertEqual(sonar._fetch_open_issues("auth", {"componentKeys": "proj"}), 1)
            self.assertEqual(
                sonar._fetch_unresolved_hotspots("auth", {"projectKey": "proj"}),
                1,
            )

    def test_sonar_helper_fallbacks_and_failure_main_path(self) -> None:
        with mock.patch.object(
            sonar,
            "_request_sonar_payload",
            return_value={"projectStatus": {}},
        ):
            self.assertEqual(
                sonar._fetch_quality_gate("auth", {"projectKey": "proj"}),
                "UNKNOWN",
            )

        with mock.patch.object(
            sonar,
            "_request_sonar_payload",
            return_value={"pullRequests": [{"key": "18", "commit": {"sha": "abc"}}]},
        ):
            self.assertEqual(sonar._fetch_pr_analysis_sha("auth", "proj", "17"), "")
        with mock.patch.object(
            sonar,
            "_request_sonar_payload",
            return_value={"pullRequests": [{"key": "17", "commit": {"sha": "abc"}}]},
        ):
            self.assertEqual(sonar._fetch_pr_analysis_sha("auth", "proj", "17"), "abc")

        findings = sonar._evaluate_findings(2, 1, "WARN")
        self.assertEqual(len(findings), 3)

        self.assertEqual(
            sonar._run_sonar_check(
                _sonar_args(
                    branch="",
                    pull_request="",
                    expected_pr_sha="",
                    max_wait_seconds=0,
                ),
                "",
            ),
            ("fail", None, None, None, ["SONAR_TOKEN is missing."]),
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            out_json = temp_path / "sonar.json"
            out_md = temp_path / "sonar.md"
            with (
                mock.patch.object(
                    sonar,
                    "quality_artifact_paths",
                    return_value=(out_json, out_md),
                ),
                mock.patch.object(
                    sonar,
                    "_run_sonar_check",
                    side_effect=RuntimeError("boom"),
                ),
                mock.patch.object(
                    sys,
                    "argv",
                    ["check_sonar_zero.py", "--project-key", SONAR_PROJECT_KEY],
                ),
                mock.patch.dict(os.environ, {"SONAR_TOKEN": "token"}, clear=True),
            ):
                self.assertEqual(sonar.main(), 1)
            self.assertIn(
                "Sonar API request failed",
                out_md.read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
