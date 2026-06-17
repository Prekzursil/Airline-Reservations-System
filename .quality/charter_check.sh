#!/usr/bin/env bash
# Charter <-> active-gate consistency check (lean 6-gate, 2026-06-16).
# Fails (exit 1) if any gate config declared in .quality/charter.yml is missing
# from the tree, so the active gate set cannot silently drift from the charter.
# Invoked by the shared reusable-quality.yml `charter-check` step.
set -euo pipefail

fail=0
require() {
  # require <path> <gate-description>
  if [ ! -e "$1" ]; then
    echo "CHARTER DRIFT: missing $1 ($2)" >&2
    fail=1
  else
    echo "ok: $1 ($2)"
  fi
}

require ".pre-commit-config.yaml" "gate 1 (lint+format+imports) + gate 5 (secrets hook)"
require "pyproject.toml"          "gate 2 (basedpyright) + gate 3 (pytest/coverage)"
require ".quality/opengrep"       "gate 4 (SAST ruleset)"
require ".gitleaks.toml"          "gate 5 (secrets allowlist)"
require "osv-scanner.toml"        "gate 6 (deps scan config)"
require ".github/dependabot.yml"  "gate 6 (Dependabot updates)"

# The charter must enforce 100% line+branch coverage (standing user policy).
if ! grep -q "fail_under = 100" pyproject.toml; then
  echo "CHARTER DRIFT: coverage gate is not pinned at 100% in pyproject.toml" >&2
  fail=1
else
  echo "ok: coverage gate pinned at 100% (gate 3)"
fi

if [ "$fail" -ne 0 ]; then
  echo "charter-check FAILED" >&2
  exit 1
fi
echo "charter-check PASSED (lean 6-gate consistent)"
