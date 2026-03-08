#!/usr/bin/env python3
from __future__ import absolute_import, annotations, division

from pathlib import Path
from typing import Iterable, Tuple

_BRANCH_PREFIXES = ("BRDA:", "BRF:", "BRH:")


def _coverage_paths(repo_root: Path | None = None) -> Tuple[Path, Path]:
    resolved_root = (repo_root or Path.cwd()).resolve()
    coverage_dir = resolved_root / "coverage" / "cpp"
    return coverage_dir / "lcov.raw.info", coverage_dir / "lcov.info"


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
