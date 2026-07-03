"""Tests for the required-checks quality gate."""

from __future__ import absolute_import, division

import os
import sys
import tempfile
from argparse import Namespace
from pathlib import Path
from unittest import TestCase, mock

from scripts import security_helpers as helpers
from scripts.quality import check_required_checks as required_checks

REPO = "owner/repo"
SHA = "a1b2c3d"
TEST_AUTH_VALUE = os.environ.get("PYTEST_FIXTURE_AUTH", "pytest-fixture-auth-value")
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


class RequiredChecksTests(TestCase):
    """Exercise the required-checks gate script."""

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
            mock.patch.object(
                required_checks, "_fetch_check_payloads", return_value=({}, {})
            ),
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
            mock.patch.object(
                required_checks, "_fetch_check_payloads", return_value=({}, {})
            ),
            mock.patch.object(required_checks, "collect_contexts", return_value={}),
            mock.patch.object(
                required_checks, "has_check_runs_in_progress", return_value=False
            ),
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
                mock.patch.dict(
                    os.environ, {"GITHUB_TOKEN": TEST_AUTH_VALUE}, clear=True
                ),
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
            mock.patch.object(
                required_checks, "_fetch_check_payloads", return_value=({}, {})
            ),
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
            mock.patch.object(
                required_checks, "has_check_runs_in_progress", return_value=False
            ),
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
                    "--repo",
                    REPO,
                    "--sha",
                    SHA,
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
