from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.quality import normalize_lcov


class NormalizeLcovTests(unittest.TestCase):
    def test_normalize_lcov_lines_strips_branch_records_only(self) -> None:
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

    def test_resolve_repo_path_rejects_absolute_and_traversal_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            previous = normalize_lcov._REPO_ROOT
            normalize_lcov._REPO_ROOT = Path(temp_dir).resolve()
            try:
                with self.assertRaises(SystemExit):
                    normalize_lcov._resolve_repo_path("../outside.info", label="input", must_exist=False)
                with self.assertRaises(SystemExit):
                    normalize_lcov._resolve_repo_path(str(Path(temp_dir).resolve() / "absolute.info"), label="output", must_exist=False)
            finally:
                normalize_lcov._REPO_ROOT = previous


if __name__ == "__main__":
    unittest.main()
