from __future__ import absolute_import, division

from io import StringIO
import unittest

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
                    "end_of_record",
                    "",
                ]
            ),
        )
        self.assertIn("Normalized LCOV: stripped 3 branch records", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
