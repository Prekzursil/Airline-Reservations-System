const fs = require("node:fs");
const path = require("node:path");

const libCoverage = require("istanbul-lib-coverage");
const libReport = require("istanbul-lib-report");
const reports = require("istanbul-reports");

const coverageDir = path.resolve(__dirname, "..", "coverage");
const coverageJsonPath = path.join(coverageDir, "coverage-final.json");

if (!fs.existsSync(coverageJsonPath)) {
  console.error(`Coverage JSON report is missing: ${coverageJsonPath}`);
  process.exit(1);
}

const coverageMap = libCoverage.createCoverageMap(require(coverageJsonPath));
const context = libReport.createContext({
  dir: coverageDir,
  coverageMap,
});

reports.create("json-summary").execute(context);
reports.create("lcovonly").execute(context);

const expectedFiles = [
  path.join(coverageDir, "coverage-summary.json"),
  path.join(coverageDir, "lcov.info"),
];

for (const filePath of expectedFiles) {
  if (!fs.existsSync(filePath)) {
    console.error(`Expected coverage artifact was not generated: ${filePath}`);
    process.exit(1);
  }
}

console.log("Generated coverage-summary.json and lcov.info from coverage-final.json.");
