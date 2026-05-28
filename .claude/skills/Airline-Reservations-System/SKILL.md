```markdown
# Airline-Reservations-System Development Patterns

> Auto-generated skill from repository analysis

## Overview
This skill provides guidance on contributing to the Airline-Reservations-System, a Python-based project for managing airline reservations. The repository emphasizes clean code, consistent quality tooling, and robust testing practices. It features Python scripts and a GUI, with workflows for deduplicating logic and aligning quality tools across the codebase.

## Coding Conventions

- **File Naming:**  
  Use `snake_case` for all Python files and modules.
  ```python
  # Good
  reservation_system.py
  seat_map.py

  # Bad
  ReservationSystem.py
  seatMap.py
  ```

- **Import Style:**  
  Prefer relative imports within packages.
  ```python
  # Good
  from .utils import parse_date

  # Bad
  from utils import parse_date
  ```

- **Export Style:**  
  Mixed usage; both explicit (`__all__`) and implicit exports are present.
  ```python
  # Explicit
  __all__ = ['ReservationSystem', 'Booking']

  # Implicit (no __all__ defined)
  ```

- **Commit Messages:**  
  Use [Conventional Commits](https://www.conventionalcommits.org/).  
  Prefixes: `refactor:`, `fix:`
  ```
  refactor: centralize seat assignment logic in helper module
  fix: correct off-by-one error in seat map rendering
  ```

## Workflows

### Deduplicate Shared Logic Across Modules
**Trigger:** When duplicated logic is identified across multiple scripts, components, or tests.  
**Command:** `/dedupe-logic`

1. **Identify** duplicated code fragments across files (e.g., helper functions, validation logic).
2. **Extract** shared logic into a new or existing helper/module.
   ```python
   # Before (duplicated in multiple files)
   def validate_seat_number(seat):
       return seat.isdigit() and 1 <= int(seat) <= 60

   # After (centralized in helpers/seat_utils.py)
   def validate_seat_number(seat):
       return seat.isdigit() and 1 <= int(seat) <= 60
   ```
3. **Refactor** original files to use the shared helper/module.
   ```python
   from helpers.seat_utils import validate_seat_number
   ```
4. **Update related tests** to use the new shared logic.
5. **Ensure test coverage** remains at 100% by running the test suite.

### Quality Tooling and Config Alignment
**Trigger:** When updating or aligning code quality tools and their configurations with organization or template standards.  
**Command:** `/sync-quality-tools`

1. **Add or update** configuration files for static analysis and security tools (e.g., `.flake8`, `.pylintrc`, `.bandit`).
2. **Update CI workflow files** to use the latest templates or SHAs.
   ```yaml
   # .github/workflows/quality-zero-gate.yml
   uses: org/quality-workflows@v2.3.1
   ```
3. **Pass through or update** required secrets/environment variables for CI gates.
4. **Fix code and tests** to comply with updated tool findings.
   ```python
   # Before (lint error: unused import)
   import os

   # After (fixed)
   # import os  # removed if unused
   ```

## Testing Patterns

- **Framework:**  
  While the main codebase is Python, some test files use `jest` (JavaScript/TypeScript), with test files matching `*.test.ts`.
- **Python Tests:**  
  Use standard Python testing practices, often with `pytest` or `unittest`.
  ```python
  # tests/test_reservation.py
  def test_seat_booking():
      assert book_seat('1A') is True
  ```
- **JavaScript/TypeScript Tests:**  
  Use `jest` for GUI components.
  ```typescript
  // airline-gui/src/components/SwapSeatsForm.test.jsx
  test('renders seat swap form', () => {
    // ...
  });
  ```

## Commands

| Command           | Purpose                                                                 |
|-------------------|-------------------------------------------------------------------------|
| /dedupe-logic     | Centralize duplicated logic into shared modules and update references.   |
| /sync-quality-tools | Update and align static analysis, linting, and security tool configs.  |
```
