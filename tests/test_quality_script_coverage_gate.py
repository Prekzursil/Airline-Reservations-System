from __future__ import absolute_import, division

import os
import json
import sys
import tempfile
import unittest
from contextlib import ExitStack, contextmanager
from pathlib import Path
from typing import Iterator
from unittest import mock

from scripts.quality import assert_coverage_100 as airline_coverage_gate


def _write_text_file(path: Path, payload: str) -> None:
    with open(os.fspath(path), "w", encoding="utf-8") as handle:
        handle.write(payload)


def _read_text_file(path: Path) -> str:
    with open(os.fspath(path), encoding="utf-8") as handle:
        return handle.read()


def _unlink_file(path: Path) -> None:
    os.unlink(os.fspath(path))


@contextmanager
def _patched_gate_paths(
    *,
    node_lcov: Path,
    cpp_lcov: Path | None = None,
    summary: Path | None = None,
    final: Path | None = None,
    out_json: Path | None = None,
    out_md: Path | None = None,
    argv: list[str] | None = None,
) -> Iterator[None]:
    with ExitStack() as stack:
        stack.enter_context(
            mock.patch.object(airline_coverage_gate, "NODE_LCOV_PATH", node_lcov)
        )
        if cpp_lcov is not None:
            stack.enter_context(
                mock.patch.object(airline_coverage_gate, "CPP_LCOV_PATH", cpp_lcov)
            )
        if summary is not None:
            stack.enter_context(
                mock.patch.object(
                    airline_coverage_gate,
                    "NODE_SUMMARY_JSON_PATH",
                    summary,
                )
            )
        if final is not None:
            stack.enter_context(
                mock.patch.object(
                    airline_coverage_gate,
                    "NODE_FINAL_JSON_PATH",
                    final,
                )
            )
        if out_json is not None and out_md is not None:
            stack.enter_context(
                mock.patch.object(
                    airline_coverage_gate,
                    "quality_artifact_paths",
                    return_value=(out_json, out_md),
                )
            )
        if argv is not None:
            stack.enter_context(mock.patch.object(sys, "argv", argv))
        yield


class AirlineCoverageGateTests(unittest.TestCase):
    """Exercise the repo's strict line and branch coverage gate script."""

    def _assert_node_stats_fallbacks(
        self,
        *,
        node_lcov: Path,
        summary: Path,
        final: Path,
    ) -> None:
        with _patched_gate_paths(
            node_lcov=node_lcov,
            summary=summary,
            final=final,
        ):
            lcov_stats = airline_coverage_gate.load_node_stats()
            _unlink_file(node_lcov)
            summary_stats = airline_coverage_gate.load_node_stats()
            _unlink_file(summary)
            final_stats = airline_coverage_gate.load_node_stats()

            self.assertEqual((lcov_stats.covered, lcov_stats.total), (2, 2))
            self.assertEqual((summary_stats.covered, summary_stats.total), (3, 4))
            self.assertEqual((final_stats.covered, final_stats.total), (1, 2))

            _unlink_file(final)
            with self.assertRaises(SystemExit):
                airline_coverage_gate.load_node_stats()

    def test_load_node_stats_prefers_known_inputs_and_evaluate_reports_failures(
        self,
    ) -> None:
        """Cover Node fallback loading and failure reporting branches."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            node_lcov = temp_path / "node.lcov"
            summary = temp_path / "summary.json"
            final = temp_path / "final.json"
            _write_text_file(node_lcov, "LF:2\nLH:2\n")
            _write_text_file(
                summary,
                json.dumps({"total": {"lines": {"covered": 3, "total": 4}}}),
            )
            _write_text_file(
                final,
                json.dumps({"a.js": {"s": {"1": 1, "2": 0}}}),
            )
            self._assert_node_stats_fallbacks(
                node_lcov=node_lcov,
                summary=summary,
                final=final,
            )

        status, findings = airline_coverage_gate.evaluate(
            [
                airline_coverage_gate.CoverageStats(
                    name="node",
                    path="node",
                    covered=3,
                    total=4,
                ),
                airline_coverage_gate.CoverageStats(
                    name="cpp",
                    path="cpp",
                    covered=1,
                    total=1,
                ),
            ]
        )
        self.assertEqual(status, "fail")
        self.assertTrue(any("node coverage below 100%" in item for item in findings))
        self.assertTrue(
            any("combined coverage below 100%" in item for item in findings)
        )

    def _run_coverage_gate_main(
        self,
        *,
        node_lcov: Path,
        cpp_lcov: Path,
        out_json: Path,
        out_md: Path,
        argv: list[str],
    ) -> int:
        with _patched_gate_paths(
            node_lcov=node_lcov,
            cpp_lcov=cpp_lcov,
            out_json=out_json,
            out_md=out_md,
            argv=argv,
        ):
            return airline_coverage_gate.main()

    def _assert_main_writes_artifacts(
        self,
        *,
        node_lcov: Path,
        cpp_lcov: Path,
        out_json: Path,
        out_md: Path,
    ) -> None:
        self.assertEqual(
            self._run_coverage_gate_main(
                node_lcov=node_lcov,
                cpp_lcov=cpp_lcov,
                out_json=out_json,
                out_md=out_md,
                argv=["assert_coverage_100.py", "--require-cpp"],
            ),
            0,
        )
        payload = json.loads(_read_text_file(out_json))
        self.assertEqual(payload["status"], "pass")
        self.assertEqual(len(payload["components"]), 2)
        self.assertIn("Coverage 100 Gate", _read_text_file(out_md))

    def _assert_require_cpp_guard(
        self,
        *,
        node_lcov: Path,
        cpp_lcov: Path,
        out_json: Path,
        out_md: Path,
    ) -> None:
        _unlink_file(cpp_lcov)
        with self.assertRaises(SystemExit):
            self._run_coverage_gate_main(
                node_lcov=node_lcov,
                cpp_lcov=cpp_lcov,
                out_json=out_json,
                out_md=out_md,
                argv=["assert_coverage_100.py", "--require-cpp"],
            )
        self.assertEqual(
            self._run_coverage_gate_main(
                node_lcov=node_lcov,
                cpp_lcov=cpp_lcov,
                out_json=out_json,
                out_md=out_md,
                argv=["assert_coverage_100.py"],
            ),
            0,
        )
        payload = json.loads(_read_text_file(out_json))
        self.assertEqual(
            [component["name"] for component in payload["components"]],
            ["node"],
        )

    def test_main_writes_artifacts_and_require_cpp_guard(self) -> None:
        """Cover artifact rendering and the optional C++ coverage requirement."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            node_lcov = temp_path / "node.lcov"
            cpp_lcov = temp_path / "cpp.lcov"
            out_json = temp_path / "coverage.json"
            out_md = temp_path / "coverage.md"
            _write_text_file(node_lcov, "LF:2\nLH:2\n")
            _write_text_file(cpp_lcov, "LF:3\nLH:3\n")
            self._assert_main_writes_artifacts(
                node_lcov=node_lcov,
                cpp_lcov=cpp_lcov,
                out_json=out_json,
                out_md=out_md,
            )
            self._assert_require_cpp_guard(
                node_lcov=node_lcov,
                cpp_lcov=cpp_lcov,
                out_json=out_json,
                out_md=out_md,
            )

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
            _write_text_file(node_lcov, "LF:1\nLH:1\n")
            _write_text_file(cpp_lcov, "LF:2\nLH:2\n")
            self.assertEqual(
                self._run_coverage_gate_main(
                    node_lcov=node_lcov,
                    cpp_lcov=cpp_lcov,
                    out_json=out_json,
                    out_md=out_md,
                    argv=["assert_coverage_100.py"],
                ),
                0,
            )
            payload = json.loads(_read_text_file(out_json))
            self.assertEqual(
                [component["name"] for component in payload["components"]],
                ["node", "cpp"],
            )
