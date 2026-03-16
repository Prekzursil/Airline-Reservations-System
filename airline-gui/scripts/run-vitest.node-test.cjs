const test = require("node:test");
const assert = require("node:assert/strict");

const { buildVitestArgs } = require("./run-vitest.cjs");

test("buildVitestArgs appends coverage filters when coverage is enabled", () => {
  const args = buildVitestArgs("vitest-entry.mjs", ["--coverage", "--watch=false"]);

  assert.deepEqual(args, [
    "vitest-entry.mjs",
    "run",
    "--coverage",
    "--watch=false",
    "--coverage.include=src/**/*.{js,jsx}",
    "--coverage.exclude=scripts/**",
  ]);
});

test("buildVitestArgs leaves non-coverage runs untouched", () => {
  const args = buildVitestArgs("vitest-entry.mjs", ["--watch=false"]);

  assert.deepEqual(args, ["vitest-entry.mjs", "run", "--watch=false"]);
});
