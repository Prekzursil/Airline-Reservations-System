---
name: quality-tooling-and-config-alignment
description: Workflow command scaffold for quality-tooling-and-config-alignment in Airline-Reservations-System.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /quality-tooling-and-config-alignment

Use this workflow when working on **quality-tooling-and-config-alignment** in `Airline-Reservations-System`.

## Goal

Synchronizes and configures static analysis, linting, and security tools across the repository to ensure consistent code quality enforcement.

## Common Files

- `.flake8`
- `.pylintrc`
- `.bandit`
- `.github/workflows/codecov-analytics.yml`
- `.github/workflows/codeql.yml`
- `.github/workflows/quality-zero-backlog.yml`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Add or update configuration files for static analysis and security tools (e.g., .flake8, .pylintrc, .bandit).
- Update CI workflow files to use the latest templates or SHAs.
- Pass through or update required secrets/environment variables for CI gates.
- Fix code and tests to comply with updated tool findings.

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.