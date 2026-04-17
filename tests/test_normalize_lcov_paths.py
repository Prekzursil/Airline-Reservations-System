"""Tests for LCOV path normalization with repo file indexes."""

from __future__ import absolute_import, division

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.quality import normalize_lcov


class NormalizeLcovPathTests(unittest.TestCase):

    """Verify LCOV path rewriting with repo file indexes."""

    def test_normalize_lcov_lines_rewrites_unique_repo_basenames(self) -> None:
        raw = [
            "TN:",
            "SF:ReservationSystem.cpp",
            "DA:10,1",
            "end_of_record",
        ]

        with TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            source_dir = Path(repo_root / "src")
            source_dir.mkdir(parents=True, exist_ok=True)
            source_path = Path(source_dir / "ReservationSystem.cpp")
            source_path.write_text("int main() { return 0; }\n", encoding="utf-8")

            normalized, stripped = normalize_lcov.normalize_lcov_lines(raw, repo_root=repo_root)

        self.assertEqual(stripped, 0)
        self.assertEqual(
            normalized,
            "\n".join(
                [
                    "TN:",
                    "SF:src/ReservationSystem.cpp",
                    "DA:10,1",
                    "LF:1",
                    "LH:1",
                    "end_of_record",
                    "",
                ]
            ),
        )


if __name__ == "__main__":
    unittest.main()
