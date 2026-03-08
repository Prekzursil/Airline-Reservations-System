#!/usr/bin/env python3
from __future__ import absolute_import, annotations, division

from pathlib import Path
from typing import Iterable, Tuple

_BRANCH_PREFIXES = ("BRDA:", "BRF:", "BRH:")
_RAW_LCOV_PATH = Path("coverage/cpp/lcov.raw.info")
_NORMALIZED_LCOV_PATH = Path("coverage/cpp/lcov.info")

def _coverage_paths() -> Tuple[Path, Path]:
    return _RAW_LCOV_PATH, _NORMALIZED_LCOV_PATH


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
    input_path, output_path = _coverage_paths()
    if not input_path.is_file():
        raise SystemExit(f"Input LCOV path does not exist: {input_path}")

    normalized, stripped_count = normalize_lcov_lines(input_path.read_text(encoding="utf-8").splitlines())
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(normalized, encoding="utf-8")
    print(f"Normalized LCOV: stripped {stripped_count} branch records from {input_path} -> {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
