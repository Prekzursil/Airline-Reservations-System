from __future__ import annotations

from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


class StaticRemediationGuardsTest(unittest.TestCase):
    def test_booking_source_avoids_y2038_sensitive_time_apis(self) -> None:
        booking_source = (REPO_ROOT / "src" / "Booking.cpp").read_text(encoding="utf-8")

        forbidden_tokens = (
            "std::time_t",
            "to_time_t",
            "localtime_r",
            "localtime_s",
            "std::put_time",
        )

        for token in forbidden_tokens:
            self.assertNotIn(token, booking_source, f"{token} should not be used in Booking.cpp")

    def test_coverage_workflow_requires_cpp_artifacts(self) -> None:
        workflow_text = (REPO_ROOT / ".github" / "workflows" / "coverage-100.yml").read_text(encoding="utf-8")
        codecov_text = (REPO_ROOT / ".github" / "workflows" / "codecov-analytics.yml").read_text(encoding="utf-8")

        self.assertIn("--require-cpp", workflow_text)
        self.assertIn("coverage/cpp/lcov.info", workflow_text)
        self.assertIn("coverage/cpp/lcov.info", codecov_text)


if __name__ == "__main__":
    unittest.main()
