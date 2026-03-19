const test = require("node:test");
const assert = require("node:assert/strict");

const { prefixCoveragePath } = require("./coverage-path-prefix.cjs");

test("prefixCoveragePath prefixes repo-relative frontend paths", () => {
  assert.equal(prefixCoveragePath("src/App.js", "airline-gui"), "airline-gui/src/App.js");
});

test("prefixCoveragePath keeps already-prefixed frontend paths intact", () => {
  assert.equal(
    prefixCoveragePath("airline-gui/src/App.js", "airline-gui"),
    "airline-gui/src/App.js",
  );
});

test("prefixCoveragePath trims embedded absolute repo paths", () => {
  assert.equal(
    prefixCoveragePath(
      "/home/runner/work/Airline-Reservations-System/Airline-Reservations-System/repo/airline-gui/src/App.js",
      "airline-gui",
    ),
    "airline-gui/src/App.js",
  );
});

test("prefixCoveragePath trims embedded Windows repo paths", () => {
  assert.equal(
    prefixCoveragePath(
      "C:\\agent\\_work\\1\\s\\airline-gui\\src\\App.js",
      "airline-gui",
    ),
    "airline-gui/src/App.js",
  );
});
