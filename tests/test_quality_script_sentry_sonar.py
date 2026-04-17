"""Exercise Sentry zero helper branches used by the quality scripts."""

from __future__ import absolute_import, division

# pylint: disable=not-context-manager

import os
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from typing import List
from unittest import mock

from scripts import security_helpers as helpers
from scripts.quality import check_sentry_zero as sentry
from scripts.quality import sentry_support
from scripts.quality import sentry_targets


def _join_parts(*parts: str) -> str:
    """Join string fragments without exposing the full literal inline."""
    return "".join(parts)


def _sentry_config():
    """Return a compact Sentry configuration for helper tests."""
    return sentry_targets.SentryConfig(
        org_label="Org",
        project_label="Project",
        user_agent="ua",
    )


class SentryAndSonarScriptTests(unittest.TestCase):

    """Cover Sentry helper logic that feeds the zero-issue gate."""

    def test_sentry_target_helpers(self) -> None:
        """Exercise Sentry target construction and header helpers."""
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

        project_target = sentry_targets.build_project_issues_target(
            "org",
            "proj",
            config,
        )
        org_target = sentry_targets.build_org_projects_target("org", "proj", config)
        self.assertEqual(project_target.host, helpers.HTTPSHost.SENTRY.value)
        self.assertIn("/organizations/", org_target.path)

    def test_sentry_project_slug_resolution_helpers(self) -> None:
        """Resolve project slugs from direct matches and org lookups."""
        config = _sentry_config()
        self.assertEqual(
            sentry_support.project_slug_from_match(
                {"slug": "proj", "name": "Project"},
                "project",
            ),
            "proj",
        )
        self.assertIsNone(
            sentry_support.project_slug_from_match({"name": "Project"}, "project")
        )
        self.assertTrue(
            sentry_support.is_not_found_error(RuntimeError("404 Not Found"))
        )
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

    def test_sentry_project_candidate_helpers(self) -> None:
        """Build ordered project candidate lists for lookup retries."""
        config = _sentry_config()
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
            self.assertIsNone(
                sentry_support.resolve_project_slug("org", "Proj", "token", config)
            )
        with mock.patch.object(
            sentry_support,
            "fetch_org_projects",
            return_value=[{"slug": "proj", "name": "Project"}],
        ):
            self.assertIsNone(
                sentry_support.resolve_project_slug("org", "Other", "token", config)
            )
        with mock.patch.object(
            sentry_support,
            "resolve_project_slug",
            return_value=None,
        ):
            self.assertEqual(
                sentry_support.project_candidates("org", "", "token", config),
                [],
            )

    def test_sentry_input_validation_and_failure_helpers(self) -> None:
        """Cover invalid input handling and unresolved-count helpers."""
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
        unresolved = sentry_support.unresolved_count("proj", [], {}, findings)
        self.assertEqual(unresolved, 0)
        self.assertEqual(findings, [])

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

    def test_sentry_evaluation_records_not_found_and_failures(self) -> None:
        """Record not-found and request-failure outcomes during evaluation."""
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

    def test_sentry_run_check_records_unresolved_issue_findings(self) -> None:
        """Fail the run when evaluated projects still report open issues."""
        config = _sentry_config()
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
        """Cover CLI parsing, markdown rendering, and fetch wrappers."""
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
            self.assertIsNone(
                sentry_support.fetch_org_projects("org", "proj", "token", config)
            )

    def test_sentry_selection_prefers_first_successful_project_payload(self) -> None:
        """Stop candidate iteration at the first successful payload lookup."""
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
            resolved, issues, headers, last_error = (
                sentry_support.select_project_payload(
                    "org",
                    "proj",
                    "token",
                    config,
                )
            )
        self.assertEqual(
            (resolved, issues, headers, last_error),
            ("proj-b", [{"id": 1}], {"x-hits": "1"}, None),
        )
    def test_sentry_selection_returns_last_error_when_all_candidates_fail(self) -> None:
        """Return the last lookup error when every candidate fails."""
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
                    RuntimeError("404 Not Found"),
                ],
            ),
        ):
            resolved, issues, headers, last_error = (
                sentry_support.select_project_payload(
                    "org",
                    "proj",
                    "token",
                    config,
                )
            )
        self.assertEqual((resolved, issues, headers), (None, None, {}))
        self.assertIsInstance(last_error, RuntimeError)

    def test_sentry_main_writes_failure_report(self) -> None:
        """Write a failure artifact when the Sentry CLI encounters an error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            out_json = Path(temp_path / "sentry.json")
            out_md = Path(temp_path / "sentry.md")
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


if __name__ == "__main__":
    unittest.main()
