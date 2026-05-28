---
name: deduplicate-shared-logic-across-modules
description: Workflow command scaffold for deduplicate-shared-logic-across-modules in Airline-Reservations-System.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /deduplicate-shared-logic-across-modules

Use this workflow when working on **deduplicate-shared-logic-across-modules** in `Airline-Reservations-System`.

## Goal

Centralizes duplicated logic or helpers into shared modules to eliminate code clones and reduce complexity, while maintaining full test coverage.

## Common Files

- `scripts/quality/gate_report.py`
- `scripts/security_http_support.py`
- `airline-gui/src/components/SeatMap.js`
- `airline-gui/src/components/SwapSeatsForm.js`
- `airline-gui/src/components/SwapSeatsForm.test.jsx`
- `tests/airplane_test.cpp`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Identify duplicated code fragments across multiple files.
- Extract shared logic into a new or existing helper/module.
- Refactor original files to use the shared helper/module.
- Update related tests to use the new shared logic.
- Ensure test coverage remains at 100%.

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.