"""Regression tests for repository coverage helper scripts."""

from __future__ import absolute_import, division

from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from scripts.quality import assert_coverage_100, normalize_lcov


class _NormalizeLcovTests(unittest.TestCase):
    """Cover LCOV normalization helpers used by the quality gate."""

    def test_normalize_lcov_lines_strips_branch_records_only(self) -> None:
        """Strip branch-only records while preserving line coverage content."""
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

        normalized, stripped = normalize_lcov.normalize_lcov_lines(raw)

        self.assertEqual(stripped, 4)
        self.assertEqual(
            normalized,
            "\n".join(
                [
                    "TN:",
                    "SF:src/example.cpp",
                    "DA:10,1",
                    "end_of_record",
                    "",
                ]
            ),
        )

    def test_main_normalizes_lcov_from_stdin_to_stdout(self) -> None:
        """Normalize LCOV input from stdin and report stripped records to stderr."""
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

        exit_code = normalize_lcov.main(
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
        )

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            stdout.getvalue(),
            "\n".join(
                [
                    "TN:",
                    "SF:src/example.cpp",
                    "DA:10,1",
                    "end_of_record",
                    "",
                ]
            ),
        )
        self.assertIn(
            "Normalized LCOV: stripped 3 branch records",
            stderr.getvalue(),
        )


class _AssertCoverageParsingTests(unittest.TestCase):
    """Exercise LCOV parsing and source-lookup behavior."""

    def test_include_lcov_line_skips_inline_and_block_exclusions(self) -> None:
        """Ignore excluded lines while keeping normal source lines eligible."""
        source_lines = (
            "// GCOVR_EXCL_START",
            "int main() {",
            "    return 0;",
            "}",
            "// GCOVR_EXCL_STOP",
            "int helper() { return 1; } // GCOVR_EXCL_LINE",
            "int covered() { return 2; }",
        )

        self.assertFalse(
            assert_coverage_100._include_lcov_line(source_lines, 2)
        )
        self.assertFalse(
            assert_coverage_100._include_lcov_line(source_lines, 3)
        )
        self.assertFalse(
            assert_coverage_100._include_lcov_line(source_lines, 6)
        )
        self.assertTrue(
            assert_coverage_100._include_lcov_line(source_lines, 7)
        )

    def test_parse_lcov_ignores_explicitly_excluded_lines(self) -> None:
        """Count only non-excluded LCOV lines when building parsed coverage stats."""
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

        with patch.dict(
            assert_coverage_100.REPO_SOURCE_LINES,
            {"src/example.cpp": source_lines},
            clear=True,
        ), TemporaryDirectory() as temp_dir:
            lcov_path = Path(temp_dir) / "sample.lcov"
            with open(lcov_path, "w", encoding="utf-8") as handle:
                handle.write(sample_lcov)

            stats = assert_coverage_100.parse_lcov("cpp", lcov_path)

        self.assertEqual(stats.total, 1)
        self.assertEqual(stats.covered, 1)

    def test_lookup_repo_source_lines_strips_repo_prefix(self) -> None:
        """Resolve cached source lines even when the LCOV path has a repo prefix."""
        source_lines = ("int covered() { return 2; }",)

        with patch.dict(
            assert_coverage_100.REPO_SOURCE_LINES,
            {"src/example.cpp": source_lines},
            clear=True,
        ):
            resolved = assert_coverage_100._lookup_repo_source_lines(
                "repo/src/example.cpp"
            )

        self.assertEqual(resolved, source_lines)


if __name__ == "__main__":
    unittest.main()
