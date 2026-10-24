#!/usr/bin/env bash
# C++ tests + STRICT 100% line AND branch coverage for src/.
#
# The QZP lean gate (reusable-quality.yml, gate 3 "compiled (go / c++)") runs
# `bash scripts/coverage-gate.sh` in every repo that ships C++ tests. This is the
# C++ coverage command this repo's quality-zero-platform profile has always used
# (profiles/repos/airline-reservations-system.yml), with the 100% assertion the
# platform applied to its lcov output now made here:
#
#   1. scripts/verify: CMake build with -DENABLE_COVERAGE=ON (gcc --coverage,
#      -O0), then ctest (the GoogleTest suite plus the two CLI smoke scenarios).
#   2. gcovr over src/ only; tests/ and the FetchContent dependencies under
#      build/_deps are not first-party code.
#      --exclude-throw-branches and --exclude-unreachable-branches drop the
#      exception-unwind and no-code branches gcc emits for C++; every
#      source-level decision is still counted.
#      The two executables' object directories are skipped: their translation
#      units are the two-line main() wrappers in src/main.cpp and
#      src/api_server_main.cpp. The bodies they call (main_body.h,
#      api_server_main_body.h) are compiled into the test binary and measured
#      there.
#   3. Fail unless every measured line and every measured branch is covered.
#
# The run also leaves coverage/cpp/lcov.info and coverage/cpp/summary.json
# (both gitignored) for anyone who wants the raw numbers.
set -euo pipefail

cd "$(dirname "$0")/.."

GCOVR_VERSION="8.7"
BUILD_DIR="${BUILD_DIR:-build}"
export BUILD_DIR

bash scripts/verify

# gcovr lives in a throwaway virtualenv outside the checkout, so nothing it
# installs is visible to the gates that scan the tree after this one.
gcovr_venv="$(mktemp -d)"
trap 'rm -rf "$gcovr_venv"' EXIT
python3 -m venv "$gcovr_venv"
"$gcovr_venv/bin/python" -m pip install --disable-pip-version-check --quiet \
  "gcovr==${GCOVR_VERSION}"
gcovr="$gcovr_venv/bin/gcovr"

mkdir -p coverage/cpp
tracefile="coverage/cpp/coverage.json"

"$gcovr" \
  --root . \
  --filter '^src/' \
  --exclude '^tests/' \
  --exclude "^${BUILD_DIR}/_deps/" \
  --object-directory "$BUILD_DIR" \
  --merge-mode-functions=merge-use-line-min \
  --gcov-exclude-directory '.*/CMakeFiles/airline_api_server.dir/.*' \
  --gcov-exclude-directory '.*/CMakeFiles/airline_reservation_system.dir/.*' \
  --exclude-throw-branches \
  --exclude-unreachable-branches \
  --json "$tracefile"

echo "::group::C++ line coverage by file (Missing = uncovered lines)"
"$gcovr" --root . --add-tracefile "$tracefile" --txt-metric line --txt
echo "::endgroup::"
echo "::group::C++ branch coverage by file (Missing = lines with an uncovered branch)"
"$gcovr" --root . --add-tracefile "$tracefile" --txt-metric branch --txt
echo "::endgroup::"

# gcovr exits 2 (line) / 4 (branch) below the bar; --print-summary always
# prints both totals first, so a failing run still shows the measured figures.
"$gcovr" --root . --add-tracefile "$tracefile" \
  --lcov coverage/cpp/lcov.info \
  --json-summary coverage/cpp/summary.json \
  --print-summary \
  --fail-under-line 100 \
  --fail-under-branch 100 || {
  echo "FAIL C++ coverage: src/ must be 100% line AND branch covered (see the per-file tables above)." >&2
  exit 1
}
echo "PASS C++ coverage: src/ is 100% line and branch covered."
