const { spawnSync } = require("node:child_process");
const path = require("node:path");

const projectRoot = path.resolve(__dirname, "..");
const vitestEntrypoint = require.resolve("vitest/vitest.mjs", {
  paths: [projectRoot],
});

const args = process.argv.slice(2);
const coverageEnabled =
  args.includes("--coverage") ||
  args.includes("--coverage.enabled") ||
  args.some((arg) => arg.startsWith("--coverage.enabled="));

const vitestArgs = [vitestEntrypoint, "run", ...args];

if (coverageEnabled) {
  vitestArgs.push("--coverage.include=src/**/*.{js,jsx}");
  vitestArgs.push("--coverage.exclude=scripts/**");
}

const vitestResult = spawnSync(process.execPath, vitestArgs, {
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
