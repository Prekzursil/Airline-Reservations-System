"""Tests for DeepScan and required-checks quality gates."""

from __future__ import absolute_import, division

import json
import os
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest import mock

from scripts import security_helpers as helpers
from scripts.quality import check_deepscan_zero as deepscan
from scripts.quality import check_required_checks as required_checks

REPO = "owner/repo"
SHA = "a1b2c3d"
TEST_AUTH_VALUE = os.environ.get("PYTEST_FIXTURE_AUTH", "pytest-fixture-auth-value")
DEEPSCAN_ARGV = [
    "check_deepscan_zero.py", "--repo", REPO, "--sha", SHA,
]
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


def _deepscan_args(**overrides):
    """Build a DeepScan gate argparse namespace."""
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
    """Build a required-checks gate argparse namespace."""
    values = {
        "repo": REPO,
        "sha": SHA,
        "timeout_seconds": 1,
        "poll_seconds": 1,
    }
    values.update(overrides)
    return Namespace(**values)


class DeepScanAndRequiredChecksTests(unittest.TestCase):
    """Exercise DeepScan and required-checks gate scripts."""

    def test_deepscan_pending_and_context_helpers(self) -> None:
        """Cover pending failure messages and context helpers."""
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
            deepscan._is_pending_context(
                {"source": "check_run", "state": "in_progress"},
            )
        )
        self.assertTrue(
            deepscan._is_pending_context(
                {"source": "status", "conclusion": "pending"},
            )
        )
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
        """Cover missing, pending, and success context paths."""
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

    def test_deepscan_parse_args_defaults(self) -> None:
        """CLI parsing maps the required-context argument."""
        with mock.patch.object(sys, "argv", DEEPSCAN_ARGV):
            args = deepscan._parse_args()
        self.assertEqual(args.required_context, "DeepScan")

    def test_deepscan_api_get_delegates_to_request_json(self) -> None:
        """_api_get returns the upstream payload unchanged."""
        target_payload = {"ok": True}
        with mock.patch.object(
            deepscan,
            "request_json_https_target",
            return_value=target_payload,
        ):
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

    def test_deepscan_poll_and_context_outcome_helpers(self) -> None:
        """Cover poll-or-timeout and context outcome branches."""
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
            deepscan._context_outcome(
                "DeepScan",
                {"source": "status", "conclusion": "success"},
            ),
            ("pass", None),
        )

    def test_deepscan_render_md_emits_none_findings(self) -> None:
        """_render_md surfaces the default 'None' bullet when findings are empty."""
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

    def test_deepscan_run_check_passes_after_pending_context(self) -> None:
        """Cover the transition from pending to success."""
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

    def test_deepscan_run_check_fails_after_missing_context_timeout(self) -> None:
        """Cover the missing-context timeout failure path."""
        args = _deepscan_args(max_wait_seconds=1)
        with (
            mock.patch.object(deepscan, "_api_get", return_value={}),
            mock.patch.object(deepscan, "collect_contexts", side_effect=[{}, {}]),
            mock.patch.object(deepscan, "_poll_or_timeout", side_effect=[True, False]),
        ):
            status, findings, observed = deepscan._run_deepscan_check(args, "token")
        self.assertEqual((status, observed), ("fail", None))
        self.assertEqual(findings, ["Missing required context: DeepScan"])

    def test_deepscan_run_check_returns_existing_failure_context(self) -> None:
        """Cover the already-failed context outcome."""
        args = _deepscan_args(max_wait_seconds=1)
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
        """Cover missing-token and failure artifact paths."""
        with (
            self.assertRaises(SystemExit),
            mock.patch.object(sys, "argv", DEEPSCAN_ARGV),
            mock.patch.dict(os.environ, {}, clear=True),
        ):
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
                mock.patch.dict(os.environ, {"GITHUB_TOKEN": TEST_AUTH_VALUE}, clear=True),
            ):
                self.assertEqual(deepscan.main(), 1)
            payload = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "fail")
            self.assertIn("broken", out_md.read_text(encoding="utf-8"))

    def test_required_checks_api_retry_and_success_payload(self) -> None:
        """Cover transient retry and successful context poll."""
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
        """Cover the missing-context polling timeout."""
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
        """Cover the passing CLI entrypoint artifact output."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            out_json = temp_path / "required.json"
            out_md = temp_path / "required.md"
            with (
                mock.patch.dict(os.environ, {"GITHUB_TOKEN": TEST_AUTH_VALUE}, clear=True),
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

    def test_required_checks_parse_args_and_api_retry_errors(self) -> None:
        """Cover CLI parsing and exhausted-retry error paths."""
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
            self.assertRaises(RuntimeError),
        ):
            required_checks._api_get(
                helpers.HTTPSRequestTarget(
                    host="api.github.com",
                    path="/repos/owner/repo",
                ),
                "token",
            )
        self.assertEqual(sleep_mock.call_count, 3)
        with (
            mock.patch.object(
                required_checks,
                "request_json_https_target",
                side_effect=helpers.HTTPSRequestError(404, "missing", "nope"),
            ),
            self.assertRaises(RuntimeError),
        ):
            required_checks._api_get(
                helpers.HTTPSRequestTarget(
                    host="api.github.com",
                    path="/repos/owner/repo",
                ),
                "token",
            )

    def test_required_checks_render_and_fetch_payload_helpers(self) -> None:
        """Cover markdown rendering and fetch payload helpers."""
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

    def test_required_checks_collect_payload_reports_failure(self) -> None:
        """_collect_payload surfaces a failing context without sleeping."""
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

    def test_required_checks_collect_payload_timeout_raises(self) -> None:
        """_collect_payload raises once the polling window is exhausted."""
        failing_args = _required_checks_args()
        with (
            mock.patch.object(required_checks.time, "time", side_effect=[0, 2]),
            mock.patch.object(required_checks, "_fetch_check_payloads"),
            self.assertRaises(RuntimeError),
        ):
            required_checks._collect_payload(
                failing_args,
                [REQUIRED_CONTEXT],
                "token",
            )

    def test_required_checks_main_exits_without_required_inputs(self) -> None:
        """main() exits when --required-context or the GITHUB_TOKEN env is absent."""
        with (
            self.assertRaises(SystemExit),
            mock.patch.object(
                sys,
                "argv",
                [
                    "check_required_checks.py",
                    "--repo", REPO,
                    "--sha", SHA,
                ],
            ),
        ):
            required_checks.main()
        with (
            self.assertRaises(SystemExit),
            mock.patch.object(sys, "argv", REQUIRED_CHECKS_ARGV),
            mock.patch.dict(os.environ, {}, clear=True),
        ):
            required_checks.main()



