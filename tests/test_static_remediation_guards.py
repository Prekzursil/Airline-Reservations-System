"""Regression guards for static-analysis-driven remediations."""

from __future__ import absolute_import, division

from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


class _StaticRemediationGuardsTest(unittest.TestCase):
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

    def test_booking_source_avoids_namespace_scope_mutable_sequence_global(self) -> None:
        booking_source = (REPO_ROOT / "src" / "Booking.cpp").read_text(encoding="utf-8")
        forbidden_globals = (
            "std::atomic_uint64_t g_bookingSequence",
            "std::atomic_uint64_t g_booking_id_sequence",
        )

        for token in forbidden_globals:
            self.assertNotIn(
                token,
                booking_source,
                "Booking.cpp should not keep the booking sequence as a namespace-scope mutable global",
            )

    def test_booking_sequence_storage_is_isolated_behind_an_accessor(self) -> None:
        booking_header = (REPO_ROOT / "src" / "Booking.h").read_text(encoding="utf-8")
        booking_source = (REPO_ROOT / "src" / "Booking.cpp").read_text(encoding="utf-8")

        self.assertIn("static std::atomic_uint64_t& bookingSequenceStorage();", booking_header)
        self.assertIn("static inline std::atomic_uint64_t bookingSequence{100};", booking_header)
        self.assertIn("return bookingSequenceStorage().fetch_add(1, std::memory_order_relaxed);", booking_source)

    def test_quality_workflows_pin_shared_platform_contracts(self) -> None:
        platform_text = (REPO_ROOT / ".github" / "workflows" / "quality-zero-platform.yml").read_text(
            encoding="utf-8"
        )
        codecov_text = (REPO_ROOT / ".github" / "workflows" / "codecov-analytics.yml").read_text(encoding="utf-8")

        self.assertIn("reusable-scanner-matrix.yml@", platform_text)
        self.assertIn("Prekzursil/quality-zero-platform", platform_text)
        self.assertIn("reusable-codecov-analytics.yml@", codecov_text)
        self.assertIn("Prekzursil/quality-zero-platform", codecov_text)


if __name__ == "__main__":
    unittest.main()
