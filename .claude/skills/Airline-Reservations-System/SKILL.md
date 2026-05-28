```markdown
# Airline-Reservations-System Development Patterns

> Auto-generated skill from repository analysis

## Overview
This skill teaches you the core development patterns and conventions used in the `Airline-Reservations-System` Python codebase. You'll learn how to structure files, write imports and exports, follow commit message guidelines, and understand the project's approach to testing. While no automated workflows were detected, this guide provides best practices and suggested commands for efficient development.

## Coding Conventions

### File Naming
- Use **kebab-case** for all file names.
  - Example:  
    ```
    flight-booking.py
    user-profile.py
    ```

### Import Style
- Use **relative imports** within the package.
  - Example:
    ```python
    from .models import Flight
    from .utils import calculate_price
    ```

### Export Style
- Use **named exports** (i.e., explicitly define what is exported).
  - Example:
    ```python
    __all__ = ['Flight', 'Booking', 'User']
    ```

### Commit Messages
- Follow the **conventional commit** pattern.
- Use the `fix` prefix for bug fixes.
- Keep commit messages concise (average ~85 characters).
  - Example:
    ```
    fix: correct seat allocation logic in booking module
    ```

## Workflows

_No automated workflows were detected in this repository. Below are suggested manual workflows for common tasks._

### Running the Application
**Trigger:** When you want to start the airline reservation system.
**Command:** `/run-app`

1. Ensure all dependencies are installed.
2. Navigate to the project root.
3. Run the main Python file:
    ```bash
    python main.py
    ```

### Adding a New Feature
**Trigger:** When implementing a new feature.
**Command:** `/add-feature`

1. Create a new Python file using kebab-case.
2. Use relative imports to connect with existing modules.
3. Define exports using `__all__`.
4. Write clear, conventional commit messages when committing changes.

### Fixing a Bug
**Trigger:** When resolving a bug in the codebase.
**Command:** `/fix-bug`

1. Identify and resolve the bug in the relevant module.
2. Write a commit message starting with `fix:`.
3. Ensure changes are covered by tests.

## Testing Patterns

- **Framework:** Unknown (no standard testing framework detected).
- **Test File Pattern:** Test files use the `*.test.ts` naming convention (suggesting some TypeScript tests, possibly for a frontend or API layer).
- **Best Practice:** Place test files alongside the modules they test, using the same naming convention.
  - Example:
    ```
    booking.test.ts
    ```

## Commands
| Command      | Purpose                                            |
|--------------|----------------------------------------------------|
| /run-app     | Run the main application                           |
| /add-feature | Scaffold and implement a new feature               |
| /fix-bug     | Fix a bug and commit with the correct convention   |
```
