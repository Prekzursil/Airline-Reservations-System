from __future__ import absolute_import, division

import os
import sys
import tempfile
import unittest
from argparse import Namespace
from contextlib import ExitStack
from pathlib import Path
from unittest import mock

from scripts import security_helpers as helpers
from scripts.quality import check_sonar_zero as sonar


SONAR_PROJECT_KEY = "Prekzursil_Airline-Reservations-System"


def _sonar_args(**overrides):
    """Build a complete argparse namespace for the Sonar zero gate."""
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


class SonarScriptTests(unittest.TestCase):
    """Exercise the hosted Sonar zero-check helper script."""

    def _assert_pull_request_scoped_run(self, args: Namespace) -> None:
        """Assert the Sonar polling helper passes for a settled PR analysis."""
        with ExitStack() as stack:
            stack.enter_context(
                mock.patch.object(sonar, "_fetch_pr_analysis_sha", return_value="want")
            )
            stack.enter_context(
                mock.patch.object(sonar, "_fetch_open_issues", return_value=0)
            )
            stack.enter_context(
                mock.patch.object(sonar, "_fetch_unresolved_hotspots", return_value=0)
            )
            stack.enter_context(
                mock.patch.object(sonar, "_fetch_quality_gate", return_value="OK")
            )
            stack.enter_context(
                mock.patch.object(sonar.time, "time", side_effect=[0, 0])
            )
            stack.enter_context(mock.patch.object(sonar.time, "sleep"))
            status, open_issues, unresolved_hotspots, quality_gate, findings = (
                sonar._run_sonar_check(args, "token")
            )

        self.assertEqual(
            (status, open_issues, unresolved_hotspots, quality_gate, findings),
            ("pass", 0, 0, "OK", []),
        )

    def _assert_main_writes_passing_artifacts(
        self,
        *,
        out_json: Path,
        out_md: Path,
    ) -> None:
        """Assert the CLI entrypoint writes pass artifacts for a clean check."""
        with ExitStack() as stack:
            stack.enter_context(
                mock.patch.object(
                    sonar,
                    "quality_artifact_paths",
                    return_value=(out_json, out_md),
                )
            )
            stack.enter_context(
                mock.patch.object(
                    sonar,
                    "_run_sonar_check",
                    return_value=("pass", 0, 0, "OK", []),
                )
            )
            stack.enter_context(
                mock.patch.object(
                    sys,
                    "argv",
                    ["check_sonar_zero.py", "--project-key", SONAR_PROJECT_KEY],
                )
            )
            stack.enter_context(
                mock.patch.dict(os.environ, {"SONAR_TOKEN": "token"}, clear=True)
            )
            self.assertEqual(sonar.main(), 0)

        self.assertIn(
            "Unresolved security hotspots: `0`",
            out_md.read_text(encoding="utf-8"),
        )

    def test_sonar_auth_and_timeout_findings(self) -> None:
        """Cover authentication, paging, and stale-analysis timeout handling."""
        self.assertTrue(sonar._auth_header("token").startswith("Basic "))
        self.assertEqual(sonar._paged_total({"paging": {"total": 5}}), 5)

        args = _sonar_args(expected_pr_sha="want", max_wait_seconds=0)
        with ExitStack() as stack:
            stack.enter_context(
                mock.patch.object(sonar, "_fetch_pr_analysis_sha", return_value="have")
            )
            stack.enter_context(
                mock.patch.object(sonar.time, "time", side_effect=[0, 1])
            )
            status, open_issues, unresolved_hotspots, quality_gate, findings = (
                sonar._run_sonar_check(args, "token")
            )
        self.assertEqual(status, "fail")
        self.assertIsNone(open_issues)
        self.assertIsNone(unresolved_hotspots)
        self.assertIsNone(quality_gate)
        self.assertIn("Expected SHA: want", findings)

    def test_sonar_success_and_main_success_path(self) -> None:
        """Cover the passing Sonar polling path once the expected SHA arrives."""
        success_args = _sonar_args(expected_pr_sha="want", max_wait_seconds=1)
        with ExitStack() as stack:
            stack.enter_context(
                mock.patch.object(
                    sonar,
                    "_fetch_pr_analysis_sha",
                    side_effect=["old", "want"],
                )
            )
            stack.enter_context(
                mock.patch.object(sonar, "_fetch_open_issues", return_value=0)
            )
            stack.enter_context(
                mock.patch.object(sonar, "_fetch_unresolved_hotspots", return_value=0)
            )
            stack.enter_context(
                mock.patch.object(sonar, "_fetch_quality_gate", return_value="OK")
            )
            stack.enter_context(
                mock.patch.object(sonar.time, "time", side_effect=[0, 0, 0, 0])
            )
            stack.enter_context(mock.patch.object(sonar.time, "sleep"))
            status, open_issues, unresolved_hotspots, quality_gate, findings = (
                sonar._run_sonar_check(success_args, "token")
            )
        self.assertEqual(
            (status, open_issues, unresolved_hotspots, quality_gate, findings),
            ("pass", 0, 0, "OK", []),
        )

    def test_sonar_branch_and_pull_request_scoped_queries(self) -> None:
        """Cover pull-request scoped checks and the passing CLI entrypoint."""
        args = _sonar_args(
            branch="",
            pull_request="17",
            expected_pr_sha="want",
            max_wait_seconds=0,
        )
        self._assert_pull_request_scoped_run(args)

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            out_json = Path(temp_path / "sonar.json")
            out_md = Path(temp_path / "sonar.md")
            self._assert_main_writes_passing_artifacts(
                out_json=out_json,
                out_md=out_md,
            )

    def test_sonar_parse_request_and_fetch_wrappers(self) -> None:
        """Cover request-target construction and response-wrapper helpers."""
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
        with ExitStack() as stack:
            stack.enter_context(
                mock.patch.object(
                    sonar,
                    "build_https_request_target",
                    return_value=request_target,
                )
            )
            stack.enter_context(
                mock.patch.object(
                    sonar,
                    "request_json_https_target",
                    return_value={"paging": {"total": 1}},
                )
            )
            payload = sonar._request_sonar_payload("auth", "/api/test")
            self.assertEqual(payload["paging"]["total"], 1)
            self.assertEqual(sonar._fetch_open_issues("auth", {"componentKeys": "proj"}), 1)
            self.assertEqual(
                sonar._fetch_unresolved_hotspots("auth", {"projectKey": "proj"}),
                1,
            )

    def test_sonar_quality_gate_and_pr_sha_helpers(self) -> None:
        """Cover quality-gate fallback and pull-request SHA extraction helpers."""
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

    def test_sonar_failure_findings_and_missing_token_path(self) -> None:
        """Cover fail findings, missing-token handling, and CLI exception output."""
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
            out_json = Path(temp_path / "sonar.json")
            out_md = Path(temp_path / "sonar.md")
            with ExitStack() as stack:
                stack.enter_context(
                    mock.patch.object(
                        sonar,
                        "quality_artifact_paths",
                        return_value=(out_json, out_md),
                    )
                )
                stack.enter_context(
                    mock.patch.object(
                        sonar,
                        "_run_sonar_check",
                        side_effect=RuntimeError("boom"),
                    )
                )
                stack.enter_context(
                    mock.patch.object(
                        sys,
                        "argv",
                        ["check_sonar_zero.py", "--project-key", SONAR_PROJECT_KEY],
                    )
                )
                stack.enter_context(
                    mock.patch.dict(os.environ, {"SONAR_TOKEN": "token"}, clear=True)
                )
                self.assertEqual(sonar.main(), 1)
            self.assertIn(
                "Sonar API request failed",
                out_md.read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
