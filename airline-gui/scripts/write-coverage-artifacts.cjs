const fs = require('node:fs');
const path = require('node:path');

const libCoverage = require('istanbul-lib-coverage');
const libReport = require('istanbul-lib-report');
const reports = require('istanbul-reports');
const { prefixCoverageMapPath } = require('./coverage-path-prefix.cjs');

const coverageDir = path.resolve(__dirname, '..', 'coverage');
const coverageJsonPath = path.join(coverageDir, 'coverage-final.json');
const coveragePrefix = 'airline-gui/';

if (!fs.existsSync(coverageJsonPath)) {
  process.stderr.write(`Coverage JSON report is missing: ${coverageJsonPath}\n`);
  process.exit(1);
}

const coverageMap = libCoverage.createCoverageMap(require(coverageJsonPath));
const prefixedCoverageMap = libCoverage.createCoverageMap({});

for (const filePath of coverageMap.files()) {
  const fileCoverage = coverageMap.fileCoverageFor(filePath).toJSON();
  fileCoverage.path = prefixCoverageMapPath(fileCoverage, coveragePrefix).path;
  prefixedCoverageMap.addFileCoverage(fileCoverage);
}

const context = libReport.createContext({
  dir: coverageDir,
  coverageMap: prefixedCoverageMap,
});

reports.create('json-summary').execute(context);
reports.create('lcovonly').execute(context);

const expectedFiles = [
  path.join(coverageDir, 'coverage-summary.json'),
  path.join(coverageDir, 'lcov.info'),
];

for (const filePath of expectedFiles) {
  if (!fs.existsSync(filePath)) {
    process.stderr.write(`Expected coverage artifact was not generated: ${filePath}\n`);
    process.exit(1);
  }
}

process.stdout.write('Generated coverage-summary.json and lcov.info from coverage-final.json.\n');
