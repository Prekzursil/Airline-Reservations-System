from __future__ import annotations

import sys
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


if __name__ == "__main__":
    unittest.main()
