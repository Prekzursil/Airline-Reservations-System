#!/usr/bin/env python3
from __future__ import absolute_import, annotations, division

import argparse
from pathlib import Path
from typing import Iterable, Tuple

_BRANCH_PREFIXES = ("BRDA:", "BRF:", "BRH:")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Normalize LCOV output so downstream tools measure line coverage consistently."
    )
    parser.add_argument("--input", required=True, help="Path to the input lcov.info file")
    parser.add_argument("--output", required=True, help="Path to the normalized output lcov.info file")
    return parser.parse_args()


def normalize_lcov_lines(lines: Iterable[str]) -> Tuple[str, int]:
    kept_lines = []
    stripped_count = 0

    for raw_line in lines:
        if raw_line.startswith(_BRANCH_PREFIXES):
            stripped_count += 1
            continue
        kept_lines.append(raw_line)

    normalized = "\n".join(kept_lines)
    if normalized and not normalized.endswith("\n"):
        normalized += "\n"
    return normalized, stripped_count


def main() -> int:
    args = _parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)

    normalized, stripped_count = normalize_lcov_lines(input_path.read_text(encoding="utf-8").splitlines())
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(normalized, encoding="utf-8")
    print(f"Normalized LCOV: stripped {stripped_count} branch records from {input_path} -> {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
