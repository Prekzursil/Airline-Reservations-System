#!/usr/bin/env python3
from __future__ import absolute_import, annotations, division

import argparse
from pathlib import Path
from typing import Iterable, Tuple

_BRANCH_PREFIXES = ("BRDA:", "BRF:", "BRH:")
_REPO_ROOT = Path.cwd().resolve()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Normalize LCOV output so downstream tools measure line coverage consistently."
    )
    parser.add_argument("--input", required=True, help="Path to the input lcov.info file")
    parser.add_argument("--output", required=True, help="Path to the normalized output lcov.info file")
    return parser.parse_args()


def _resolve_repo_path(raw_path: str, *, label: str, must_exist: bool) -> Path:
    candidate = Path((raw_path or "").strip())
    if not str(candidate):
        raise SystemExit(f"{label} path is required")
    if candidate.is_absolute():
        raise SystemExit(f"{label} path must be relative to the repository root")

    resolved = (_REPO_ROOT / candidate).resolve()
    try:
        resolved.relative_to(_REPO_ROOT)
    except ValueError as exc:
        raise SystemExit(f"{label} path must stay within the repository root") from exc

    if must_exist and not resolved.is_file():
        raise SystemExit(f"{label} path does not exist: {candidate}")

    return resolved


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
    input_path = _resolve_repo_path(args.input, label="input", must_exist=True)
    output_path = _resolve_repo_path(args.output, label="output", must_exist=False)

    normalized, stripped_count = normalize_lcov_lines(input_path.read_text(encoding="utf-8").splitlines())
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(normalized, encoding="utf-8")
    print(f"Normalized LCOV: stripped {stripped_count} branch records from {input_path} -> {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
