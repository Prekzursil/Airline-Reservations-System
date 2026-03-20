from __future__ import absolute_import, annotations, division

import importlib.util
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "tests" / "test_run_cli_scenario.py"
MODULE_SPEC = importlib.util.spec_from_file_location("airline_run_cli_scenario", MODULE_PATH)
if MODULE_SPEC is None or MODULE_SPEC.loader is None:  # pragma: no cover - import guard
    raise RuntimeError(f"Unable to load test helper module from {MODULE_PATH}")
run_cli_scenario = importlib.util.module_from_spec(MODULE_SPEC)
sys.modules[MODULE_SPEC.name] = run_cli_scenario
MODULE_SPEC.loader.exec_module(run_cli_scenario)


class RunCliScenarioScriptTests(unittest.TestCase):
    def test_resolve_scenario_uses_allowlisted_inputs(self) -> None:
        scenario = run_cli_scenario._resolve_scenario("cli_exit")

        self.assertEqual(
            scenario.input_file,
            run_cli_scenario.REPO_ROOT / "tests" / "cli_exit_input.txt",
        )
        self.assertIn("Welcome to the Airline Reservation System!", scenario.expected_fragments)
        self.assertIn("Exiting system. Goodbye!", scenario.expected_fragments)

    def test_resolve_binary_uses_current_working_directory_allowlist(self) -> None:
        with TemporaryDirectory() as temp_dir:
            binary_dir = Path(temp_dir)
            binary_path = binary_dir / "airline_reservation_system"
            binary_path.write_text("", encoding="utf-8")

            resolved = run_cli_scenario._resolve_binary(binary_dir)

        self.assertEqual(resolved.resolve(), binary_path.resolve())


if __name__ == "__main__":
    unittest.main()
