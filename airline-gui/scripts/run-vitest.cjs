const { spawnSync } = require("node:child_process");
const path = require("node:path");

const projectRoot = path.resolve(__dirname, "..");
const vitestEntrypoint = require.resolve("vitest/vitest.mjs", {
  paths: [projectRoot],
});

/**
 * Build the args vector to pass to the vitest entrypoint, layering
 * coverage-include/exclude globs when the caller asked for coverage.
 *
 * @param {string} entrypoint - Resolved path to the vitest module to spawn.
 * @param {string[]} args - User-supplied CLI args (raw process.argv slice).
 * @returns {string[]} The full argv (entrypoint + flags) to invoke.
 */
function buildVitestArgs(entrypoint, args) {
  const coverageEnabled =
    args.includes("--coverage") ||
    args.includes("--coverage.enabled") ||
    args.some((arg) => arg.startsWith("--coverage.enabled="));

  return coverageEnabled
    ? [
        entrypoint,
        "run",
        ...args,
        "--coverage.include=src/**/*.{js,jsx}",
        "--coverage.exclude=scripts/**",
      ]
    : [entrypoint, "run", ...args];
}

/**
 * Run vitest (with coverage post-processing when requested) and exit
 * with vitest's status. Used as the package "test" script entrypoint.
 *
 * @param {string[]} [args] - Override CLI args. Defaults to process.argv.
 */
function run(args = process.argv.slice(2)) {
  const coverageEnabled =
    args.includes("--coverage") ||
    args.includes("--coverage.enabled") ||
    args.some((arg) => arg.startsWith("--coverage.enabled="));

  const vitestResult = spawnSync(process.execPath, buildVitestArgs(vitestEntrypoint, args), {
    cwd: projectRoot,
    stdio: "inherit",
  });

  if (vitestResult.status !== 0) {
    process.exit(vitestResult.status ?? 1);
  }

  if (coverageEnabled) {
    const writerPath = path.resolve(__dirname, "write-coverage-artifacts.cjs");
    const writerResult = spawnSync(process.execPath, [writerPath], {
      cwd: projectRoot,
      stdio: "inherit",
    });

    if (writerResult.status !== 0) {
      process.exit(writerResult.status ?? 1);
    }
  }
}

if (require.main === module) {
  run();
}

module.exports = { buildVitestArgs, run };
