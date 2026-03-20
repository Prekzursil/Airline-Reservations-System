from __future__ import absolute_import, division

import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.quality import coverage_parsers as parsers
from scripts.quality import normalize_lcov

@contextlib.contextmanager
def _temporary_cwd(path: Path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


@contextlib.contextmanager
def _normalize_lcov_fixture():
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_root = Path(temp_dir)
        source_dir = Path(repo_root / "src")
        source_dir.mkdir(parents=True, exist_ok=True)
        main_source = Path(source_dir / "main.cpp")
        main_source.write_text(
            "int main() { return 0; }\n",
            encoding="utf-8",
        )
        named_source = Path(source_dir / "named.py")
        named_source.write_text(
            "print('hello')\n",
            encoding="utf-8",
        )
        ignored_source = Path(repo_root / "ignored.py")
        ignored_source.write_text(
            "print('ignore')\n",
            encoding="utf-8",
        )

        original_is_file = Path.is_file

        def _patched_is_file(path: Path) -> bool:
            if path.name == "ignored.py":
                raise OSError("access denied")
            return original_is_file(path)

        with mock.patch.object(Path, "is_file", new=_patched_is_file):
            repo_paths, repo_file_index = normalize_lcov._build_repo_file_indexes(repo_root)

        yield repo_root, repo_paths, repo_file_index


@contextlib.contextmanager
def _coverage_parser_fixture():
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        lcov_path = Path(temp_path / "coverage.lcov")
        lcov_path.write_text(
            "\n".join(
                [
                    "SF:repo/src/sample.cpp",
                    "DA:1,1",
                    "DA:2,0",
                    "DA:3,0",
                    "DA:4,0",
                    "DA:5,0",
                    "DA:6,0",
                    "DA:7,0",
                    "DA:8,1",
                    "end_of_record",
                    "SF:repo/src/fallback.cpp",
                    "LF:4",
                    "LH:3",
                    "end_of_record",
                ]
            ),
            encoding="utf-8",
        )
        summary_path = Path(temp_path / "summary.json")
        summary_path.write_text(
            json.dumps({"total": {"lines": {"covered": 4, "total": 5}}}),
            encoding="utf-8",
        )
        fallback_summary = Path(temp_path / "fallback-summary.json")
        fallback_summary.write_text(
            json.dumps({"total": {"statements": {"covered": 3, "total": 4}}}),
            encoding="utf-8",
        )
        final_path = Path(temp_path / "final.json")
        final_path.write_text(
            json.dumps(
                {
                    "a.js": {"s": {"1": 1, "2": 0}},
                    "b.js": {"s": {"1": 2}},
                    "bad": [],
                }
            ),
            encoding="utf-8",
        )
        yield lcov_path, summary_path, fallback_summary, final_path


class CoverageParsersAndNormalizeLCOVTests(unittest.TestCase):
    def test_repo_index_and_source_path_helpers_cover_edge_cases(self) -> None:
        with _normalize_lcov_fixture() as (repo_root, repo_paths, repo_file_index):
            self.assertEqual(repo_file_index["main.cpp"], ["src/main.cpp"])
            self.assertNotIn("ignored.py", repo_file_index)
            self.assertEqual(
                normalize_lcov._sanitize_relative_candidate("./src/main.cpp"),
                "src/main.cpp",
            )
            self.assertEqual(
                normalize_lcov._sanitize_relative_candidate("../main.cpp"),
                "main.cpp",
            )
            self.assertEqual(
                normalize_lcov._trim_to_source_suffix(
                    "build/CMakeFiles/airline.dir/src/main.cpp.gcda"
                ),
                "build/CMakeFiles/airline.dir/src/main.cpp",
            )
            self.assertEqual(
                normalize_lcov._trim_to_source_suffix("coverage-report.txt"),
                "coverage-report.txt",
            )
            self.assertEqual(
                normalize_lcov._matching_repo_suffix(
                    "build/CMakeFiles/airline.dir/src/main.cpp.gcda",
                    repo_paths,
                ),
                "src/main.cpp",
            )
            self.assertEqual(
                normalize_lcov._matching_repo_suffix("src/main.cpp", repo_paths),
                "src/main.cpp",
            )
            self.assertEqual(
                normalize_lcov._matching_repo_suffix("../main.cpp", repo_paths),
                "main.cpp",
            )
            self.assertEqual(
                normalize_lcov._normalize_source_path(
                    "././src/main.cpp",
                    repo_root=repo_root,
                    repo_paths=repo_paths,
                    repo_file_index=repo_file_index,
                ),
                "src/main.cpp",
            )
            self.assertEqual(
                normalize_lcov._normalize_source_path(
                    "SRC/MAIN.CPP",
                    repo_root=repo_root,
                    repo_paths=repo_paths,
                    repo_file_index=repo_file_index,
                ),
                "src/main.cpp",
            )
            self.assertEqual(
                normalize_lcov._normalize_source_path(
                    "",
                    repo_root=repo_root,
                    repo_paths=repo_paths,
                    repo_file_index=repo_file_index,
                ),
                "",
            )
            self.assertEqual(
                normalize_lcov._normalize_source_path(
                    f"{repo_root.resolve(strict=False).as_posix()}/src/main.cpp",
                    repo_root=repo_root,
                    repo_paths=repo_paths,
                    repo_file_index=repo_file_index,
                ),
                "src/main.cpp",
            )
            self.assertEqual(
                normalize_lcov._normalize_source_path(
                    repo_root.resolve(strict=False).as_posix(),
                    repo_root=repo_root,
                    repo_paths=repo_paths,
                    repo_file_index=repo_file_index,
                ),
                "",
            )
            self.assertEqual(
                normalize_lcov._normalize_source_path(
                    "C:/outside/named.py",
                    repo_root=repo_root,
                    repo_paths=repo_paths,
                    repo_file_index=repo_file_index,
                ),
                "src/named.py",
            )
            self.assertEqual(
                normalize_lcov._normalize_source_path(
                    "reports/no-match.txt",
                    repo_root=repo_root,
                    repo_paths=repo_paths,
                    repo_file_index=repo_file_index,
                ),
                "reports/no-match.txt",
            )

    def test_normalize_lcov_lines_and_main_strip_branch_records(self) -> None:
        with _normalize_lcov_fixture() as (repo_root, _, _):
            normalized, stripped = normalize_lcov.normalize_lcov_lines(
                [
                    "TN:",
                    "SF:build/CMakeFiles/airline.dir/src/main.cpp.gcda",
                    "BRDA:1,0,0,1",
                    "DA:1,1",
                    "end_of_record",
                    f"SF:{(repo_root / 'src' / 'named.py').as_posix()}",
                    "BRF:1",
                    "DA:2,1",
                    "end_of_record",
                ],
                repo_root=repo_root,
            )
            self.assertEqual(stripped, 2)
            self.assertEqual(
                normalized,
                "TN:\nSF:src/main.cpp\nDA:1,1\nLF:1\nLH:1\nend_of_record\n"
                "SF:src/named.py\nDA:2,1\nLF:1\nLH:1\nend_of_record\n",
            )

            stdout = io.StringIO()
            stderr = io.StringIO()
            with _temporary_cwd(repo_root):
                result = normalize_lcov.main(
                    stdin=io.StringIO(
                        "SF:build/CMakeFiles/app.dir/src/main.cpp.gcno\nBRH:1\nDA:2,1\n"
                    ),
                    stdout=stdout,
                    stderr=stderr,
                )
            self.assertEqual(result, 0)
            self.assertEqual(stdout.getvalue(), "SF:src/main.cpp\nDA:2,1\nLF:1\nLH:1\n")
            self.assertIn("stripped 1 branch records", stderr.getvalue())

    def test_normalize_source_path_matches_casefolded_suffix_for_outside_paths(self) -> None:
        with _normalize_lcov_fixture() as (repo_root, repo_paths, repo_file_index):
            self.assertEqual(
                normalize_lcov._normalize_source_path(
                    "C:/outside/SRC/MAIN.CPP.gcda",
                    repo_root=repo_root,
                    repo_paths=repo_paths,
                    repo_file_index=repo_file_index,
                ),
                "src/main.cpp",
            )

    def test_normalize_lcov_lines_synthesizes_lf_lh_from_da_records(self) -> None:
        with _normalize_lcov_fixture() as (repo_root, _, _):
            normalized, stripped = normalize_lcov.normalize_lcov_lines(
                [
                    "SF:C:/outside/SRC/MAIN.CPP.gcda",
                    "DA:1,1",
                    "DA:2,0",
                    "end_of_record",
                ],
                repo_root=repo_root,
            )

        self.assertEqual(stripped, 0)
        self.assertEqual(
            normalized,
            "SF:src/main.cpp\nDA:1,1\nDA:2,0\nLF:2\nLH:1\nend_of_record\n",
        )

    def test_normalize_lcov_lines_preserves_existing_lf_lh_records(self) -> None:
        with _normalize_lcov_fixture() as (repo_root, _, _):
            normalized, stripped = normalize_lcov.normalize_lcov_lines(
                [
                    "SF:src/main.cpp",
                    "DA:1,1",
                    "LF:4",
                    "LH:2",
                    "end_of_record",
                ],
                repo_root=repo_root,
            )

        self.assertEqual(stripped, 0)
        self.assertEqual(
            normalized,
            "SF:src/main.cpp\nDA:1,1\nLF:4\nLH:2\nend_of_record\n",
        )

    def test_lcov_and_istanbul_parsers_cover_fallback_and_exclusions(self) -> None:
        parsers._excluded_line_numbers.cache_clear()
        with _coverage_parser_fixture() as (
            lcov_path,
            summary_path,
            fallback_summary,
            final_path,
        ):
            sample_lines = (
                "int a = 1;",
                "{",
                "do_skip(); // GCOVR_EXCL_LINE",
                "value += 1;",
                "// GCOVR_EXCL_START",
                "never_count();",
                "// GCOVR_EXCL_STOP",
                "return 0;",
            )

            with mock.patch.dict(
                parsers.REPO_SOURCE_LINES,
                {"src/sample.cpp": sample_lines},
                clear=False,
            ):
                lcov_stats = parsers.parse_lcov("cpp", lcov_path)

            summary_stats = parsers.parse_istanbul_summary("node", summary_path)
            fallback_stats = parsers.parse_istanbul_summary(
                "node-fallback",
                fallback_summary,
            )
            final_stats = parsers.parse_istanbul_final("node-final", final_path)

        self.assertEqual((lcov_stats.covered, lcov_stats.total), (5, 7))
        self.assertEqual((summary_stats.covered, summary_stats.total), (4, 5))
        self.assertEqual((fallback_stats.covered, fallback_stats.total), (3, 4))
        self.assertEqual((final_stats.covered, final_stats.total), (2, 3))
        self.assertIsNone(parsers._lookup_repo_source_lines("/abs/path.cpp"))
        self.assertEqual(parsers._safe_int("bad"), 0)

    def test_parser_helper_branches_cover_empty_inputs_and_repo_prefixes(self) -> None:
        self.assertEqual(
            parsers.CoverageStats(name="empty", path="x", covered=0, total=0).percent, 100.0
        )
        self.assertTrue(parsers._include_lcov_line(None, 0))
        self.assertIsNone(parsers._lookup_repo_source_lines("../escape.cpp"))
        with mock.patch.dict(
            parsers.REPO_SOURCE_LINES,
            {"src/ReservationSystem.cpp": ("int handleReservation();",)},
            clear=False,
        ):
            self.assertEqual(
                parsers._lookup_repo_source_lines("./src/ReservationSystem.cpp"),
                ("int handleReservation();",),
            )

        repo_relative = "src/sample.cpp"
        sample_lines = ("int main() {", "return 0;", "}")
        repo_prefixed = parsers.REPO_ROOT.as_posix().rstrip("/") + "/" + repo_relative
        with mock.patch.dict(parsers.REPO_SOURCE_LINES, {repo_relative: sample_lines}, clear=False):
            self.assertEqual(parsers._lookup_repo_source_lines(repo_prefixed), sample_lines)
            self.assertEqual(
                parsers._lookup_repo_source_lines(f"repo/{repo_relative}"), sample_lines
            )

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            not_dict_path = Path(temp_path / "not-dict.json")
            not_dict_path.write_text(json.dumps(["bad"]), encoding="utf-8")
            bad_statements_path = Path(temp_path / "bad-statements.json")
            bad_statements_path.write_text(json.dumps({"a.js": {"s": []}}), encoding="utf-8")

            not_dict_stats = parsers.parse_istanbul_final("node", not_dict_path)
            bad_statement_stats = parsers.parse_istanbul_final("node", bad_statements_path)

        self.assertEqual((not_dict_stats.covered, not_dict_stats.total), (0, 0))
        self.assertEqual((bad_statement_stats.covered, bad_statement_stats.total), (0, 0))

