const { spawnSync } = require("node:child_process");
const path = require("node:path");

const args = process.argv.slice(2);
const coverageEnabled =
  args.includes("--coverage") ||
  args.includes("--coverage.enabled") ||
  args.some((arg) => arg.startsWith("--coverage.enabled="));

const vitestArgs = ["vitest", "run", ...args];

if (coverageEnabled) {
  vitestArgs.push("--coverage.include=src/**/*.{js,jsx}");
  vitestArgs.push("--coverage.exclude=scripts/**");
}

const vitestResult = spawnSync("npx", vitestArgs, {
  cwd: path.resolve(__dirname, ".."),
  stdio: "inherit",
  shell: process.platform === "win32",
});

if (vitestResult.status !== 0) {
  process.exit(vitestResult.status ?? 1);
}

if (coverageEnabled) {
  const writerPath = path.resolve(__dirname, "write-coverage-artifacts.cjs");
  const writerResult = spawnSync(process.execPath, [writerPath], {
    cwd: path.resolve(__dirname, ".."),
    stdio: "inherit",
  });

  if (writerResult.status !== 0) {
    process.exit(writerResult.status ?? 1);
  }
}
