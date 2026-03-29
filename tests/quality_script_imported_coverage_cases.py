"""Cover quality script helper branches with DeepSource-friendly test structure."""

from __future__ import absolute_import, division

import contextlib
import io
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
from scripts.quality import check_codacy_zero as codacy
from scripts.quality import check_quality_secrets as quality_secrets
from scripts.quality import github_contexts
from scripts.quality import required_checks_support


@contextlib.contextmanager
def _temporary_cwd(path: Path):
    """Temporarily switch the working directory for filesystem-based script tests."""
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


class GitHubContextSupportTests(unittest.TestCase):
    """Exercise context collection helpers used by the required-checks gate."""

    def test_collect_context_entries_and_required_context_evaluation(self) -> None:
        """Collect contexts from check runs and statuses and evaluate requirements."""
        check_runs_payload = {
            "check_runs": [
                {
                    "name": "Codecov Analytics",
                    "status": "completed",
                    "conclusion": "success",
                },
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
        """Ignore blank names and keep failure helper outputs stable."""
        entries = github_contexts.collect_context_entries(
            [
                {"name": "  ", "status": "completed", "conclusion": "success"},
                {
                    "name": "Codecov Analytics",
                    "status": "queued",
                    "conclusion": "neutral",
                },
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


class QualitySecretsAndCodacyTests(unittest.TestCase):
    """Cover quality-secrets and Codacy zero helper branches."""

    def test_quality_secret_helpers_cover_dedupe_presence_and_main_success(
        self,
    ) -> None:
        """Verify environment helpers and the sanitized quality-secrets CLI path."""
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
            with _temporary_cwd(temp_path), mock.patch.dict(
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
            ), mock.patch.object(sys, "argv", ["check_quality_secrets.py"]):
                self.assertEqual(quality_secrets.main(), 0)
                out_json, _ = helpers.quality_artifact_paths(
                    helpers.QualityArtifact.QUALITY_SECRETS
                )
                with io.open(
                    os.fspath(out_json),
                    encoding="utf-8",
                ) as payload_file:
                    payload = json.load(payload_file)
                self.assertTrue(payload["details_omitted"])

    def test_codacy_helpers_and_main_cover_success_failure_and_token_resolution(
        self,
    ) -> None:
        """Cover Codacy helper paths for success, failure, and CLI report output."""
        nested_total = {"outer": [{"hits": 3}]}
        self.assertEqual(codacy.extract_total_open(nested_total), 3)
        self.assertIsNone(codacy.extract_total_open({"results": []}))

        with mock.patch.dict(os.environ, {"CODACY_API_TOKEN": "env-token"}, clear=True):
            self.assertEqual(codacy._resolve_token(""), "env-token")

        args = Namespace(
            provider="gh",
            owner="Prekzursil",
            repo="Airline-Reservations-System",
            branch="",
        )
        self.assertEqual(
            codacy._run_codacy_check(args, ""),
            (None, ["CODACY_API_TOKEN is missing."], "fail"),
        )

        with mock.patch.object(codacy, "_fetch_open_issues", return_value=0):
            open_issues, findings, status = codacy._run_codacy_check(args, "token")
        self.assertEqual((open_issues, findings, status), (0, [], "pass"))

        with mock.patch.object(
            codacy,
            "_fetch_open_issues",
            side_effect=RuntimeError("boom"),
        ):
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
            with mock.patch.object(
                codacy,
                "quality_artifact_paths",
                return_value=(out_json, out_md),
            ), mock.patch.object(
                codacy,
                "_run_codacy_check",
                return_value=(0, [], "pass"),
            ), mock.patch.object(sys, "argv", cli_args):
                self.assertEqual(codacy.main(), 0)

            with io.open(os.fspath(out_json), encoding="utf-8") as payload_file:
                payload = json.load(payload_file)
            self.assertEqual(payload["status"], "pass")
            self.assertEqual(payload["open_issues"], 0)

    def test_codacy_render_and_status_branches(self) -> None:
        """Check Codacy markdown and fail-state helper rendering."""
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
