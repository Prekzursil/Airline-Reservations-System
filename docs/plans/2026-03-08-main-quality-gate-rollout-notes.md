# Main Quality Gate Rollout Notes

## Baseline Failure

- Workflow: `Quality Zero Gate`
- Run ID: `22793633260`
- Commit: `004d2ce56b30ec3c945cc2e002ebf2d27e776202`
- Failure mode: missing required context `Codacy Static Code Analysis`

## Branch Protection Contexts

### Before

```json
[
  "verify",
  "Coverage 100 Gate",
  "Codecov Analytics",
  "Quality Zero Gate",
  "SonarCloud Code Analysis",
  "Codacy Static Code Analysis",
  "DeepScan",
  "Sentry Zero",
  "Sonar Zero",
  "Codacy Zero",
  "DeepScan Zero",
  "Semgrep Zero"
]
```

### After

```json
[
  "verify",
  "Coverage 100 Gate",
  "Codecov Analytics",
  "Quality Zero Gate",
  "SonarCloud Code Analysis",
  "DeepScan",
  "Sentry Zero",
  "Sonar Zero",
  "Codacy Zero",
  "DeepScan Zero",
  "Semgrep Zero"
]
```

## Protection Invariants Rechecked

- Required approving review count: `1`
- Required conversation resolution: `true`
- Strict status checks: `true`

## PR Validation Status

- PR: `#20`
- PR URL: `https://github.com/Prekzursil/Airline-Reservations-System/pull/20`
- Branch: `codex/quality-zero-gate-codacy-context`
- Commit: `89db3f5ae6ff65ecffec2b2df46561b491661cdb`

## Residual Blocker

- PR-triggered GitHub Actions jobs did not start on GitHub-hosted runners.
- Representative runs:
  - `Quality Zero Gate`: `22828854169`
  - `Verify`: `22828854171`
- Check-run annotation on failed jobs:

```text
The job was not started because your account is locked due to a billing issue.
```

- Result: the workflow change is in place, but branch validation cannot complete until the GitHub Actions billing lock is cleared on the repository owner account.
