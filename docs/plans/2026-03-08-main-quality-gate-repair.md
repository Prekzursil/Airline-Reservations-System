# Airline Main Quality Gate Repair Plan

> **For Codex:** Execute this from a fresh clone on branch `codex/quality-zero-gate-codacy-context`, not from the detached snapshot workspace.

**Goal:** Remove the obsolete `Codacy Static Code Analysis` requirement that keeps `Quality Zero Gate` red while preserving the existing repo-owned and still-reporting vendor gates.

**Architecture:** Treat this as a minimal governance and workflow repair. Keep the repo-owned zero gates in place, remove only the missing Codacy vendor context from the aggregate workflow and `main` branch protection, and verify the fix through a branch PR before merge.

**Tech Stack:** GitHub Actions YAML, GitHub branch protection via `gh api`, Node/Vitest, WSL bash, `make`, `g++`, `cmake.exe`

---

## Summary

- Work only from `C:\Users\Prekzursil\Downloads\Airline-Reservations-System-live`.
- Branch from remote `main` using `codex/quality-zero-gate-codacy-context`.
- Keep `Coverage 100 Gate`, `Codecov Analytics`, `Sonar Zero`, `Codacy Zero`, `Semgrep Zero`, `Sentry Zero`, `DeepScan Zero`, `SonarCloud Code Analysis`, and `DeepScan`.
- Remove only `Codacy Static Code Analysis` from the aggregate workflow and from `main` branch protection.

## Baseline

- Current failing run: `Quality Zero Gate` run `22793633260` on commit `004d2ce56b30ec3c945cc2e002ebf2d27e776202`.
- Current missing context: `Codacy Static Code Analysis`.
- Fresh-clone baseline commands:
  - `git remote -v`
  - `git branch -vv`
  - `gh repo view Prekzursil/Airline-Reservations-System --json defaultBranchRef,name,url`
  - `gh api repos/Prekzursil/Airline-Reservations-System/branches/main/protection/required_status_checks/contexts`
  - `gh run view 22793633260 --repo Prekzursil/Airline-Reservations-System --log`

## Environment Repair

- Rename the dead WSL shim `/home/prekzursil/.local/bin/cmake` so it no longer shadows usable CMake.
- Use `cmake.exe` from Windows in WSL if plain `cmake` is unavailable and passwordless `sudo` is not available for installing native CMake.
- Verify:
  - `wsl.exe -e bash -lc 'command -v cmake.exe && cmake.exe --version'`
  - `wsl.exe -e bash -lc 'command -v make && make --version | sed -n "1,2p"'`
  - `wsl.exe -e bash -lc 'command -v g++ && g++ --version | sed -n "1,2p"'`

## Repo Changes

- Update `.github/workflows/quality-zero-gate.yml`.
- Remove only this line from the required-context list:
  - `--required-context "Codacy Static Code Analysis" \`
- Leave all other required contexts unchanged.

## Branch Protection

- Replace the `main` required-status-check list with exactly:
  - `verify`
  - `Coverage 100 Gate`
  - `Codecov Analytics`
  - `Quality Zero Gate`
  - `SonarCloud Code Analysis`
  - `DeepScan`
  - `Sentry Zero`
  - `Sonar Zero`
  - `Codacy Zero`
  - `DeepScan Zero`
  - `Semgrep Zero`
- Do not change review requirements, conversation resolution, or any other protection settings.

## Verification

- Local repo verification:
  - `npm --prefix airline-gui ci`
  - `npm --prefix airline-gui test -- --coverage --watch=false`
  - `npm --prefix airline-gui run build`
  - `wsl.exe -e bash -lc 'cd /mnt/c/Users/Prekzursil/Downloads/Airline-Reservations-System-live && PATH="$PATH:/mnt/c/Program Files/CMake/bin" bash scripts/verify'`
- PR verification:
  - `gh pr checks <pr-number> --repo Prekzursil/Airline-Reservations-System`
  - Confirm `Quality Zero Gate` is green and no longer waits on `Codacy Static Code Analysis`.

## Delivery

- Commit the workflow change on `codex/quality-zero-gate-codacy-context`.
- Open a human-reviewed PR labeled `risk:low`.
- State in the PR that the repo-owned `Codacy Zero` gate remains required and only the obsolete missing vendor context was removed.
