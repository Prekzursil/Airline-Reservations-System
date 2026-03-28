"""Coverage helper regressions for the Airline repo's local quality scripts."""

from __future__ import absolute_import, division

from io import StringIO
import json
import os
from pathlib import Path
from typing import Dict
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from scripts.quality import assert_coverage_100, normalize_lcov


def _write_text(path: Path, content: str) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)


def _mkdir(path: Path) -> None:
    os.makedirs(path, exist_ok=True)


def _unlink(path: Path) -> None:
    os.remove(path)


class NormalizeLcovTests(unittest.TestCase):
    """Behavioral checks for the LCOV normalization helper."""

    def test_normalize_lcov_lines_preserves_branch_records(self) -> None:
        raw = [
            "TN:",
            "SF:src/example.cpp",
            "DA:10,1",
            "BRDA:10,0,0,1",
            "BRDA:10,0,1,-",
            "BRF:2",
            "BRH:1",
            "end_of_record",
        ]

        normalized, preserved = normalize_lcov.normalize_lcov_lines(raw)

        self.assertEqual(preserved, 4)
        self.assertEqual(
            normalized,
            "\n".join(
                [
                    "TN:",
                    "SF:src/example.cpp",
                    "DA:10,1",
                    "BRDA:10,0,0,1",
                    "BRDA:10,0,1,-",
                    "BRF:2",
                    "BRH:1",
                    "end_of_record",
                    "",
                ]
            ),
        )

    def test_main_normalizes_lcov_from_stdin_to_stdout(self) -> None:
        stdin = StringIO(
            "\n".join(
                [
                    "TN:",
                    "SF:src/example.cpp",
                    "DA:10,1",
                    "BRDA:10,0,0,1",
                    "BRF:1",
                    "BRH:1",
                    "end_of_record",
                    "",
                ]
            )
        )
        stdout = StringIO()
        stderr = StringIO()

        exit_code = normalize_lcov.main(stdin=stdin, stdout=stdout, stderr=stderr)

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            stdout.getvalue(),
            "\n".join(
                [
                    "TN:",
                    "SF:src/example.cpp",
                    "DA:10,1",
                    "BRDA:10,0,0,1",
                    "BRF:1",
                    "BRH:1",
                    "end_of_record",
                    "",
                ]
            ),
        )
        self.assertIn("Normalized LCOV: preserved 3 branch records", stderr.getvalue())


class AssertCoverageParsingTests(unittest.TestCase):
    """Parsing and reporting coverage for the Airline repo's helper scripts."""

    def test_coverage_stats_branch_percent_defaults_to_full_when_no_branch_total(self) -> None:
        stats = assert_coverage_100.CoverageStats(
            name="node",
            path="node.lcov",
            covered=0,
            total=0,
            branch_covered=0,
            branch_total=0,
        )

        self.assertEqual(stats.percent, 100.0)
        self.assertEqual(stats.branch_percent, 100.0)

    def test_include_lcov_line_skips_inline_and_block_exclusions(self) -> None:
        source_lines = (
            "// GCOVR_EXCL_START",
            "int main() {",
            "    return 0;",
            "}",
            "// GCOVR_EXCL_STOP",
            "int helper() { return 1; } // GCOVR_EXCL_LINE",
            "int covered() { return 2; }",
        )

        self.assertFalse(assert_coverage_100._include_lcov_line(source_lines, 2))
        self.assertFalse(assert_coverage_100._include_lcov_line(source_lines, 3))
        self.assertFalse(assert_coverage_100._include_lcov_line(source_lines, 6))
        self.assertTrue(assert_coverage_100._include_lcov_line(source_lines, 7))

    def test_include_lcov_line_handles_missing_source_metadata(self) -> None:
        self.assertTrue(assert_coverage_100._include_lcov_line(None, 0))
        self.assertTrue(assert_coverage_100._include_lcov_line(("line",), 5))

    def test_parse_lcov_ignores_explicitly_excluded_lines(self) -> None:
        sample_lcov = "\n".join(
            [
                "TN:",
                "SF:src/example.cpp",
                "DA:2,0",
                "DA:3,0",
                "DA:4,0",
                "DA:6,0",
                "DA:7,1",
                "end_of_record",
                "",
            ]
        )

        source_lines = (
            "// GCOVR_EXCL_START",
            "int main() {",
            "    return 0;",
            "}",
            "// GCOVR_EXCL_STOP",
            "int helper() { return 1; } // GCOVR_EXCL_LINE",
            "int covered() { return 2; }",
        )

        with patch.dict(assert_coverage_100.REPO_SOURCE_LINES, {"src/example.cpp": source_lines}, clear=True):
            with TemporaryDirectory() as temp_dir:
                lcov_path = Path(temp_dir) / "sample.lcov"
                with open(lcov_path, "w", encoding="utf-8") as handle:
                    handle.write(sample_lcov)

                stats = assert_coverage_100.parse_lcov("cpp", lcov_path)

        self.assertEqual(stats.total, 1)
        self.assertEqual(stats.covered, 1)
        self.assertEqual(stats.branch_total, 0)
        self.assertEqual(stats.branch_covered, 0)

    def test_parse_lcov_tracks_branch_totals_when_present(self) -> None:
        with TemporaryDirectory() as temp_dir:
            lcov_path: Path = Path(temp_dir) / "sample.lcov"
            _write_text(
                lcov_path,
                "\n".join(
                    [
                        "TN:",
                        "SF:src/example.cpp",
                        "DA:1,1",
                        "BRDA:1,0,0,1",
                        "BRDA:1,0,1,0",
                        "BRF:2",
                        "BRH:1",
                        "end_of_record",
                        "",
                    ]
                ),
            )

            with patch.dict(
                assert_coverage_100.REPO_SOURCE_LINES,
                {"src/example.cpp": ("int covered() { return 2; }",)},
                clear=True,
            ):
                stats = assert_coverage_100.parse_lcov("cpp", lcov_path)

        self.assertEqual(stats.total, 1)
        self.assertEqual(stats.covered, 1)
        self.assertEqual(stats.branch_total, 2)
        self.assertEqual(stats.branch_covered, 1)

    def test_lookup_repo_source_lines_strips_repo_prefix(self) -> None:
        source_lines = ("int covered() { return 2; }",)

        with patch.dict(assert_coverage_100.REPO_SOURCE_LINES, {"src/example.cpp": source_lines}, clear=True):
            resolved = assert_coverage_100._lookup_repo_source_lines("repo/src/example.cpp")

        self.assertEqual(resolved, source_lines)

    def test_lookup_repo_source_lines_rejects_parent_traversal_and_absolute_paths(self) -> None:
        self.assertIsNone(assert_coverage_100._lookup_repo_source_lines("../src/example.cpp"))
        self.assertIsNone(assert_coverage_100._lookup_repo_source_lines("/abs/path/example.cpp"))

    def test_lookup_repo_source_lines_trims_repo_root_prefix(self) -> None:
        source_lines = ("int covered() { return 2; }",)
        raw_path = f"{assert_coverage_100.REPO_ROOT.as_posix()}/src/example.cpp"

        with patch.dict(
            assert_coverage_100.REPO_SOURCE_LINES,
            {"src/example.cpp": source_lines},
            clear=True,
        ):
            resolved = assert_coverage_100._lookup_repo_source_lines(raw_path)

        self.assertEqual(resolved, source_lines)

    def test_parse_istanbul_summary_falls_back_to_statements_when_lines_are_missing(self) -> None:
        with TemporaryDirectory() as temp_dir:
            summary_path: Path = Path(temp_dir) / "coverage-summary.json"
            _write_text(
                summary_path,
                '{"total":{"lines":{"covered":0,"total":0},"statements":{"covered":3,"total":3}}}',
            )

            stats = assert_coverage_100.parse_istanbul_summary("node", summary_path)

        self.assertEqual(stats.covered, 3)
        self.assertEqual(stats.total, 3)

    def test_parse_istanbul_final_counts_statement_hits(self) -> None:
        with TemporaryDirectory() as temp_dir:
            final_path: Path = Path(temp_dir) / "coverage-final.json"
            _write_text(
                final_path,
                '{"src/App.js":{"s":{"1":1,"2":0}},"src/Other.js":{"s":{"3":2}}}',
            )

            stats = assert_coverage_100.parse_istanbul_final("node", final_path)

        self.assertEqual(stats.covered, 2)
        self.assertEqual(stats.total, 3)
        self.assertEqual(stats.branch_total, 0)
        self.assertEqual(stats.branch_covered, 0)

    def test_parse_istanbul_final_handles_non_dict_entries_and_branch_arrays(self) -> None:
        with TemporaryDirectory() as temp_dir:
            final_path: Path = Path(temp_dir) / "coverage-final.json"
            _write_text(
                final_path,
                json.dumps(
                    {
                        "skip": "string-entry",
                        "src/App.js": {"s": {"1": 1}, "b": {"0": [1, 0]}},
                        "src/Other.js": {"s": "bad", "b": {"1": "bad"}},
                    }
                ),
            )

            stats = assert_coverage_100.parse_istanbul_final("node", final_path)

        self.assertEqual(stats.covered, 1)
        self.assertEqual(stats.total, 1)
        self.assertEqual(stats.branch_covered, 1)
        self.assertEqual(stats.branch_total, 2)

    def test_parse_istanbul_final_returns_empty_stats_for_non_dict_root(self) -> None:
        with TemporaryDirectory() as temp_dir:
            final_path: Path = Path(temp_dir) / "coverage-final.json"
            _write_text(final_path, '["not-a-dict"]')

            stats = assert_coverage_100.parse_istanbul_final("node", final_path)

        self.assertEqual(stats.covered, 0)
        self.assertEqual(stats.total, 0)
        self.assertEqual(stats.branch_covered, 0)
        self.assertEqual(stats.branch_total, 0)

    def test_load_node_stats_prefers_summary_then_final(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root: Path = Path(temp_dir)
            summary_path: Path = root / "coverage-summary.json"
            final_path: Path = root / "coverage-final.json"
            _write_text(
                summary_path,
                '{"total":{"lines":{"covered":2,"total":2}}}',
            )
            _write_text(final_path, '{"src/App.js":{"s":{"1":1}}}')

            with patch.object(
                assert_coverage_100,
                "NODE_LCOV_PATH",
                root / "missing.info",
            ), patch.object(
                assert_coverage_100,
                "NODE_SUMMARY_JSON_PATH",
                summary_path,
            ), patch.object(
                assert_coverage_100,
                "NODE_FINAL_JSON_PATH",
                final_path,
            ):
                stats = assert_coverage_100.load_node_stats()

            self.assertEqual(stats.covered, 2)
            self.assertEqual(stats.total, 2)

            _unlink(summary_path)
            with patch.object(
                assert_coverage_100,
                "NODE_LCOV_PATH",
                root / "missing.info",
            ), patch.object(
                assert_coverage_100,
                "NODE_SUMMARY_JSON_PATH",
                summary_path,
            ), patch.object(
                assert_coverage_100,
                "NODE_FINAL_JSON_PATH",
                final_path,
            ):
                stats = assert_coverage_100.load_node_stats()

            self.assertEqual(stats.covered, 1)
            self.assertEqual(stats.total, 1)

    def test_load_node_stats_errors_when_all_node_artifacts_are_missing(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root: Path = Path(temp_dir)
            summary_path: Path = root / "coverage-summary.json"
            final_path: Path = root / "coverage-final.json"

            with patch.object(
                assert_coverage_100,
                "NODE_LCOV_PATH",
                root / "missing.info",
            ), patch.object(
                assert_coverage_100,
                "NODE_SUMMARY_JSON_PATH",
                summary_path,
            ), patch.object(
                assert_coverage_100,
                "NODE_FINAL_JSON_PATH",
                final_path,
            ):
                with self.assertRaises(SystemExit):
                    assert_coverage_100.load_node_stats()

    def test_load_node_stats_prefers_lcov_when_present(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root: Path = Path(temp_dir)
            lcov_path: Path = root / "coverage.info"
            summary_path: Path = root / "coverage-summary.json"
            final_path: Path = root / "coverage-final.json"
            _write_text(
                lcov_path,
                "TN:\nSF:src/example.cpp\nDA:1,1\nBRF:1\nBRH:1\nend_of_record\n",
            )
            _write_text(summary_path, '{"total":{"lines":{"covered":0,"total":0}}}')
            _write_text(final_path, '{"src/App.js":{"s":{"1":0}}}')

            with patch.object(assert_coverage_100, "NODE_LCOV_PATH", lcov_path), patch.object(
                assert_coverage_100,
                "NODE_SUMMARY_JSON_PATH",
                summary_path,
            ), patch.object(
                assert_coverage_100,
                "NODE_FINAL_JSON_PATH",
                final_path,
            ), patch.dict(
                assert_coverage_100.REPO_SOURCE_LINES,
                {"src/example.cpp": ("int covered() { return 1; }",)},
                clear=True,
            ):
                stats = assert_coverage_100.load_node_stats()

        self.assertEqual(stats.covered, 1)
        self.assertEqual(stats.total, 1)

    def test_evaluate_reports_component_and_combined_failures(self) -> None:
        failing = assert_coverage_100.CoverageStats(name="node", path="node.lcov", covered=9, total=10)
        passing = assert_coverage_100.CoverageStats(name="cpp", path="cpp.lcov", covered=1, total=1)

        status, findings = assert_coverage_100.evaluate([failing, passing])

        self.assertEqual(status, "fail")
        self.assertTrue(any("node coverage below 100%" in item for item in findings))
        self.assertTrue(any("combined coverage below 100%" in item for item in findings))

    def test_evaluate_enforces_branch_thresholds_when_requested(self) -> None:
        failing = assert_coverage_100.CoverageStats(
            name="node",
            path="node.lcov",
            covered=10,
            total=10,
            branch_covered=1,
            branch_total=2,
        )
        passing = assert_coverage_100.CoverageStats(
            name="cpp",
            path="cpp.lcov",
            covered=1,
            total=1,
            branch_covered=1,
            branch_total=1,
        )

        status, findings = assert_coverage_100.evaluate([failing, passing], branch_min_percent=100.0)

        self.assertEqual(status, "fail")
        self.assertTrue(
            any("node branch coverage below 100.00%" in item for item in findings)
        )
        self.assertTrue(
            any(
                "combined branch coverage below 100.00%" in item
                for item in findings
            )
        )

    def test_evaluate_reports_missing_branch_data_when_required(self) -> None:
        stats = [
            assert_coverage_100.CoverageStats(
                name="node",
                path="node.lcov",
                covered=1,
                total=1,
                branch_covered=0,
                branch_total=0,
            )
        ]

        status, findings = assert_coverage_100.evaluate(stats, branch_min_percent=100.0)

        self.assertEqual(status, "fail")
        self.assertIn("node branch coverage data missing from node.lcov", findings)

    def test_render_md_handles_empty_components_and_findings(self) -> None:
        payload: Dict[str, object] = {
            "status": "pass",
            "timestamp_utc": "2026-03-28T00:00:00+00:00",
            "branch_min_percent": None,
            "components": [],
            "findings": [],
        }

        rendered = assert_coverage_100._render_md(payload)

        self.assertIn("- None", rendered)
        self.assertIn("Minimum required branch coverage: `disabled`", rendered)

    def test_main_requires_cpp_artifact_when_requested(self) -> None:
        with TemporaryDirectory() as temp_dir:
            previous = Path.cwd()
            os.chdir(temp_dir)
            try:
                coverage_root: Path = Path("airline-gui") / "coverage"
                _mkdir(coverage_root)
                _write_text(
                    coverage_root / "coverage-summary.json",
                    '{"total":{"lines":{"covered":1,"total":1}}}',
                )

                with patch("sys.argv", ["assert_coverage_100.py", "--require-cpp"]):
                    with self.assertRaises(SystemExit):
                        assert_coverage_100.main()
            finally:
                os.chdir(previous)

    def test_main_enforces_branch_threshold_argument(self) -> None:
        with TemporaryDirectory() as temp_dir:
            previous = Path.cwd()
            os.chdir(temp_dir)
            try:
                coverage_root: Path = Path("airline-gui") / "coverage"
                _mkdir(coverage_root)
                _write_text(
                    coverage_root / "lcov.info",
                    "\n".join(
                        [
                            "TN:",
                            "SF:airline-gui/src/App.js",
                            "LF:1",
                            "LH:1",
                            "BRF:2",
                            "BRH:1",
                            "end_of_record",
                            "",
                        ]
                    ),
                )

                with patch.object(sys, "argv", ["assert_coverage_100.py", "--branch-min-percent", "100"]):
                    rc = assert_coverage_100.main()
            finally:
                os.chdir(previous)

        self.assertEqual(rc, 1)

    def test_main_adds_cpp_stats_when_artifact_exists_without_require_flag(self) -> None:
        with TemporaryDirectory() as temp_dir:
            previous = Path.cwd()
            os.chdir(temp_dir)
            try:
                coverage_root: Path = Path("airline-gui") / "coverage"
                _mkdir(coverage_root)
                _write_text(
                    coverage_root / "coverage-summary.json",
                    '{"total":{"lines":{"covered":1,"total":1},"branches":{"covered":1,"total":1}}}',
                )
                cpp_coverage_root: Path = Path("coverage") / "cpp"
                _mkdir(cpp_coverage_root)
                _write_text(
                    cpp_coverage_root / "lcov.info",
                    "TN:\nSF:src/example.cpp\nDA:1,1\nBRF:1\nBRH:1\nend_of_record\n",
                )

                with patch.object(assert_coverage_100, "REPO_SOURCE_LINES", {"src/example.cpp": ("int covered() { return 1; }",)}):
                    with patch.object(sys, "argv", ["assert_coverage_100.py"]):
                        rc = assert_coverage_100.main()
            finally:
                os.chdir(previous)

        self.assertEqual(rc, 0)

    def test_main_runs_via_runpy_with_require_cpp(self) -> None:
        import runpy

        with TemporaryDirectory() as temp_dir:
            previous = Path.cwd()
            os.chdir(temp_dir)
            try:
                coverage_root: Path = Path("airline-gui") / "coverage"
                _mkdir(coverage_root)
                _write_text(
                    coverage_root / "coverage-summary.json",
                    '{"total":{"lines":{"covered":1,"total":1},"branches":{"covered":1,"total":1}}}',
                )
                cpp_coverage_root: Path = Path("coverage") / "cpp"
                _mkdir(cpp_coverage_root)
                _write_text(
                    cpp_coverage_root / "lcov.info",
                    "TN:\nSF:src/example.cpp\nDA:1,1\nBRF:1\nBRH:1\nend_of_record\n",
                )

                with patch.object(
                    assert_coverage_100,
                    "REPO_SOURCE_LINES",
                    {"src/example.cpp": ("int covered() { return 1; }",)},
                ), patch.object(
                    sys,
                    "argv",
                    ["assert_coverage_100.py", "--require-cpp"],
                ):
                    with self.assertRaises(SystemExit) as exc:
                        runpy.run_path(
                            str(Path(assert_coverage_100.__file__)),
                            run_name="__main__",
                        )
            finally:
                os.chdir(previous)

        self.assertEqual(exc.exception.code, 0)


if __name__ == "__main__":
    unittest.main()
