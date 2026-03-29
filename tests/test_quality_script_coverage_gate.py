from __future__ import absolute_import, division

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.quality import assert_coverage_100 as airline_coverage_gate


class AirlineCoverageGateTests(unittest.TestCase):
    """Exercise the repo's strict line and branch coverage gate script."""

    def test_load_node_stats_prefers_known_inputs_and_evaluate_reports_failures(self) -> None:
        """Cover Node fallback loading and failure reporting branches."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            node_lcov = temp_path / "node.lcov"
            node_lcov.write_text("LF:2\nLH:2\n", encoding="utf-8")
            summary = temp_path / "summary.json"
            summary.write_text(
                json.dumps({"total": {"lines": {"covered": 3, "total": 4}}}), encoding="utf-8"
            )
            final = temp_path / "final.json"
            final.write_text(json.dumps({"a.js": {"s": {"1": 1, "2": 0}}}), encoding="utf-8")

            with (
                mock.patch.object(airline_coverage_gate, "NODE_LCOV_PATH", node_lcov),
                mock.patch.object(airline_coverage_gate, "NODE_SUMMARY_JSON_PATH", summary),
                mock.patch.object(airline_coverage_gate, "NODE_FINAL_JSON_PATH", final),
            ):
                lcov_stats = airline_coverage_gate.load_node_stats()
                node_lcov.unlink()
                summary_stats = airline_coverage_gate.load_node_stats()
                summary.unlink()
                final_stats = airline_coverage_gate.load_node_stats()

                self.assertEqual((lcov_stats.covered, lcov_stats.total), (2, 2))
                self.assertEqual((summary_stats.covered, summary_stats.total), (3, 4))
                self.assertEqual((final_stats.covered, final_stats.total), (1, 2))

                final.unlink()
                with self.assertRaises(SystemExit):
                    airline_coverage_gate.load_node_stats()

        status, findings = airline_coverage_gate.evaluate(
            [
                airline_coverage_gate.CoverageStats(name="node", path="node", covered=3, total=4),
                airline_coverage_gate.CoverageStats(name="cpp", path="cpp", covered=1, total=1),
            ]
        )
        self.assertEqual(status, "fail")
        self.assertTrue(any("node coverage below 100%" in item for item in findings))
        self.assertTrue(any("combined coverage below 100%" in item for item in findings))

    def test_main_writes_artifacts_and_require_cpp_guard(self) -> None:
        """Cover artifact rendering and the optional C++ coverage requirement."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            node_lcov = temp_path / "node.lcov"
            cpp_lcov = temp_path / "cpp.lcov"
            out_json = temp_path / "coverage.json"
            out_md = temp_path / "coverage.md"
            node_lcov.write_text("LF:2\nLH:2\n", encoding="utf-8")
            cpp_lcov.write_text("LF:3\nLH:3\n", encoding="utf-8")

            with (
                mock.patch.object(airline_coverage_gate, "NODE_LCOV_PATH", node_lcov),
                mock.patch.object(airline_coverage_gate, "CPP_LCOV_PATH", cpp_lcov),
                mock.patch.object(
                    airline_coverage_gate, "quality_artifact_paths", return_value=(out_json, out_md)
                ),
                mock.patch.object(sys, "argv", ["assert_coverage_100.py", "--require-cpp"]),
            ):
                self.assertEqual(airline_coverage_gate.main(), 0)

            payload = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "pass")
            self.assertEqual(len(payload["components"]), 2)
            self.assertIn("Coverage 100 Gate", out_md.read_text(encoding="utf-8"))

            cpp_lcov.unlink()
            with (
                mock.patch.object(airline_coverage_gate, "NODE_LCOV_PATH", node_lcov),
                mock.patch.object(airline_coverage_gate, "CPP_LCOV_PATH", cpp_lcov),
                mock.patch.object(
                    airline_coverage_gate, "quality_artifact_paths", return_value=(out_json, out_md)
                ),
                mock.patch.object(sys, "argv", ["assert_coverage_100.py", "--require-cpp"]),
                self.assertRaises(SystemExit),
            ):
                airline_coverage_gate.main()

            with (
                mock.patch.object(airline_coverage_gate, "NODE_LCOV_PATH", node_lcov),
                mock.patch.object(airline_coverage_gate, "CPP_LCOV_PATH", cpp_lcov),
                mock.patch.object(
                    airline_coverage_gate, "quality_artifact_paths", return_value=(out_json, out_md)
                ),
                mock.patch.object(sys, "argv", ["assert_coverage_100.py"]),
            ):
                self.assertEqual(airline_coverage_gate.main(), 0)
            payload = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertEqual([component["name"] for component in payload["components"]], ["node"])

    def test_render_optional_cpp_and_arg_parse_branches(self) -> None:
        """Cover markdown rendering and optional C++ component selection paths."""
        with mock.patch.object(sys, "argv", ["assert_coverage_100.py"]):
            args = airline_coverage_gate._parse_args()
        self.assertFalse(args.require_cpp)

        rendered = airline_coverage_gate._render_md(
            {
                "status": "pass",
                "timestamp_utc": "2026-03-19T00:00:00+00:00",
                "components": [],
                "findings": [],
            }
        )
        self.assertIn("## Components", rendered)
        self.assertIn("- None", rendered)
        self.assertIn(
            "- below target",
            airline_coverage_gate._render_md(
                {
                    "status": "fail",
                    "timestamp_utc": "2026-03-19T00:00:00+00:00",
                    "components": [],
                    "findings": ["below target"],
                }
            ),
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            node_lcov = temp_path / "node.lcov"
            cpp_lcov = temp_path / "cpp.lcov"
            out_json = temp_path / "coverage.json"
            out_md = temp_path / "coverage.md"
            node_lcov.write_text("LF:1\nLH:1\n", encoding="utf-8")
            cpp_lcov.write_text("LF:2\nLH:2\n", encoding="utf-8")
            with (
                mock.patch.object(airline_coverage_gate, "NODE_LCOV_PATH", node_lcov),
                mock.patch.object(airline_coverage_gate, "CPP_LCOV_PATH", cpp_lcov),
                mock.patch.object(
                    airline_coverage_gate, "quality_artifact_paths", return_value=(out_json, out_md)
                ),
                mock.patch.object(sys, "argv", ["assert_coverage_100.py"]),
            ):
                self.assertEqual(airline_coverage_gate.main(), 0)
            payload = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertEqual(
                [component["name"] for component in payload["components"]], ["node", "cpp"]
            )
