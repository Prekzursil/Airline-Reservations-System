from __future__ import annotations

import os
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

    def test_main_normalizes_repo_default_lcov_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            previous_cwd = Path.cwd()
            try:
                os.chdir(temp_dir)
                raw_path = Path("coverage/cpp/lcov.raw.info")
                raw_path.parent.mkdir(parents=True, exist_ok=True)
                raw_path.write_text(
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
                    encoding="utf-8",
                )

                exit_code = normalize_lcov.main()

                self.assertEqual(exit_code, 0)
                self.assertEqual(
                    Path("coverage/cpp/lcov.info").read_text(encoding="utf-8"),
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
            finally:
                os.chdir(previous_cwd)


if __name__ == "__main__":
    unittest.main()
