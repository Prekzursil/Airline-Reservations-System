#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(
            f"usage: {argv[0]} <binary> <input-file> [expected-fragment...]",
            file=sys.stderr,
        )
        return 2

    binary = Path(argv[1])
    input_file = Path(argv[2])
    expected_fragments = argv[3:]

    with input_file.open("r", encoding="utf-8") as handle:
        completed = subprocess.run(
            [str(binary)],
            stdin=handle,
            text=True,
            capture_output=True,
            check=False,
        )

    output = completed.stdout.replace("\r", "")

    if completed.returncode != 0:
        if output:
            print(output, file=sys.stderr, end="" if output.endswith("\n") else "\n")
        if completed.stderr:
            print(
                completed.stderr,
                file=sys.stderr,
                end="" if completed.stderr.endswith("\n") else "\n",
            )
        return completed.returncode

    for expected in expected_fragments:
        if expected not in output:
            print(f"missing expected output fragment: {expected}", file=sys.stderr)
            print("--- output ---", file=sys.stderr)
            print(output, file=sys.stderr, end="" if output.endswith("\n") else "\n")
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
