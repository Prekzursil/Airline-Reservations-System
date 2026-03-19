#!/usr/bin/env python3
from __future__ import annotations

import subprocess  # nosec B404 - test harness executes a locally built allowlisted binary without shell expansion
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ALLOWED_BINARY_NAMES = (
    "airline_reservation_system",
    "airline_reservation_system.exe",
)
KNOWN_BUILD_SUBDIRECTORIES = ("", "Debug", "Release", "RelWithDebInfo", "MinSizeRel")


@dataclass(frozen=True)
class Scenario:
    input_file: Path
    expected_fragments: tuple[str, ...]


SCENARIOS = {
    "cli_exit": Scenario(
        input_file=REPO_ROOT / "tests" / "cli_exit_input.txt",
        expected_fragments=(
            "Welcome to the Airline Reservation System!",
            "Exiting system. Goodbye!",
            "Thank you for using the Airline Reservation System.",
        ),
    ),
    "cli_menu_flow": Scenario(
        input_file=REPO_ROOT / "tests" / "cli_menu_flow_input.txt",
        expected_fragments=(
            "Customer Coverage User with ID CUST0003 added successfully.",
            "Booking successful! Booking ID:",
            "Airplane FL303 added successfully.",
        ),
    ),
}


def _print_usage(program_name: str) -> int:
    available = ", ".join(sorted(SCENARIOS))
    print(f"usage: {program_name} <scenario>", file=sys.stderr)
    print(f"available scenarios: {available}", file=sys.stderr)
    return 2


def _resolve_scenario(name: str) -> Scenario:
    scenario = SCENARIOS.get(name)
    if scenario is None:
        available = ", ".join(sorted(SCENARIOS))
        raise ValueError(f"unknown scenario '{name}'. Expected one of: {available}")
    return scenario


def _binary_candidates(binary_dir: Path) -> list[Path]:
    candidates: list[Path] = []
    for subdirectory in KNOWN_BUILD_SUBDIRECTORIES:
        search_root = binary_dir if not subdirectory else binary_dir / subdirectory
        for binary_name in ALLOWED_BINARY_NAMES:
            candidates.append(search_root / binary_name)
    return candidates


def _resolve_binary(binary_dir: Path) -> Path:
    resolved_binary_dir = binary_dir.resolve()
    for candidate in _binary_candidates(resolved_binary_dir):
        if candidate.is_file():
            return candidate
    searched = ", ".join(str(candidate) for candidate in _binary_candidates(resolved_binary_dir))
    raise ValueError(f"unable to locate allowlisted airline CLI binary. Searched: {searched}")


def _run_binary(binary: Path, scenario: Scenario) -> subprocess.CompletedProcess[str]:
    input_text = scenario.input_file.read_text(encoding="utf-8")
    return subprocess.run(  # nosec B603 - _resolve_binary restricts execution to a fixed local allowlist
        [str(binary)],
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
    )


def _print_process_output(output: str, error_output: str) -> None:
    if output:
        print(output, file=sys.stderr, end="" if output.endswith("\n") else "\n")
    if error_output:
        print(
            error_output,
            file=sys.stderr,
            end="" if error_output.endswith("\n") else "\n",
        )


def _assert_expected_fragments(output: str, expected_fragments: list[str]) -> int:
    for expected in expected_fragments:
        if expected not in output:
            print(f"missing expected output fragment: {expected}", file=sys.stderr)
            print("--- output ---", file=sys.stderr)
            print(output, file=sys.stderr, end="" if output.endswith("\n") else "\n")
            return 1
    return 0


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        return _print_usage(argv[0])

    try:
        scenario = _resolve_scenario(argv[1])
        binary = _resolve_binary(Path.cwd())
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    completed = _run_binary(binary, scenario)
    output = completed.stdout.replace("\r", "")

    if completed.returncode != 0:
        _print_process_output(output, completed.stderr)
        return completed.returncode

    return _assert_expected_fragments(output, list(scenario.expected_fragments))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
