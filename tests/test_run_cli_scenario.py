#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ALLOWED_BINARY_ROOTS = (
    REPO_ROOT / "build",
    REPO_ROOT / "build-clang",
    REPO_ROOT / "build-gcc",
)
ALLOWED_BINARY_NAMES = {
    "ReservationSystemTests",
    "ReservationSystemTests.exe",
    "airline_reservation_system",
    "airline_reservation_system.exe",
}
ALLOWED_INPUT_ROOT = REPO_ROOT / "tests"


def _print_usage(program_name: str) -> int:
    print(
        f"usage: {program_name} <binary> <input-file> [expected-fragment...]",
        file=sys.stderr,
    )
    return 2


def _resolve_required_file(raw_path: str, *, label: str) -> Path:
    candidate = Path(raw_path)
    resolved = candidate if candidate.is_absolute() else REPO_ROOT / candidate
    resolved = resolved.resolve()
    if not resolved.is_file():
        raise ValueError(f"{label} does not exist: {resolved}")
    return resolved


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _resolve_binary(raw_path: str) -> Path:
    binary = _resolve_required_file(raw_path, label="binary")
    if binary.name not in ALLOWED_BINARY_NAMES:
        raise ValueError(f"binary is not allowlisted: {binary.name}")
    if not any(_is_within(binary, root) for root in ALLOWED_BINARY_ROOTS):
        raise ValueError(f"binary must live under a known build directory: {binary}")
    return binary


def _resolve_input_file(raw_path: str) -> Path:
    input_file = _resolve_required_file(raw_path, label="input file")
    if not _is_within(input_file, ALLOWED_INPUT_ROOT):
        raise ValueError(f"input file must live under tests/: {input_file}")
    return input_file


def _run_binary(binary: Path, input_file: Path) -> subprocess.CompletedProcess[str]:
    with input_file.open("r", encoding="utf-8") as handle:
        return subprocess.run(
            [os.fspath(binary)],
            stdin=handle,
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
    if len(argv) < 3:
        return _print_usage(argv[0])

    try:
        binary = _resolve_binary(argv[1])
        input_file = _resolve_input_file(argv[2])
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    completed = _run_binary(binary, input_file)
    output = completed.stdout.replace("\r", "")

    if completed.returncode != 0:
        _print_process_output(output, completed.stderr)
        return completed.returncode

    return _assert_expected_fragments(output, argv[3:])


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
