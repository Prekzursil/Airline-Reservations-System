const { spawnSync } = require("node:child_process");
const path = require("node:path");

const projectRoot = path.resolve(__dirname, "..");
const vitestEntrypoint = require.resolve("vitest/vitest.mjs", {
  paths: [projectRoot],
});

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
