/**
 * Strip trailing forward slashes off a path string.
 *
 * @param {string} value - Path or path prefix.
 * @returns {string} Same path with no trailing "/".
 */
function trimTrailingSlashes(value) {
  let normalizedValue = value;
  while (normalizedValue.endsWith("/")) {
    normalizedValue = normalizedValue.slice(0, -1);
  }
  return normalizedValue;
}

/**
 * Strip leading "./" segments off a relative path.
 *
 * @param {string} value - Relative path that may be prefixed with "./".
 * @returns {string} Path without the leading "./" segments.
 */
function trimLeadingCurrentDirectory(value) {
  let normalizedValue = value;
  while (normalizedValue.startsWith("./")) {
    normalizedValue = normalizedValue.slice(2);
  }
  return normalizedValue;
}

/**
 * Re-anchor a vitest-emitted file path under the supplied prefix so
 * SonarCloud / Codecov / qlty can map it back to the airline-gui/ tree.
 *
 * @param {string} filePath - Raw vitest path.
 * @param {string} prefix - Repo-relative prefix to anchor under (e.g. "airline-gui").
 * @returns {string} Normalized, prefixed path.
 */
function prefixCoveragePath(filePath, prefix) {
  const normalizedPrefix = trimTrailingSlashes(prefix.replaceAll("\\", "/"));
  const normalizedPath = trimLeadingCurrentDirectory(filePath.replaceAll("\\", "/"));

  if (!normalizedPrefix) {
    return normalizedPath;
  }

  if (normalizedPath.startsWith(`${normalizedPrefix}/`)) {
    return normalizedPath;
  }

  const embeddedPrefix = `/${normalizedPrefix}/`;
  const embeddedPrefixIndex = normalizedPath.lastIndexOf(embeddedPrefix);
  if (embeddedPrefixIndex >= 0) {
    return normalizedPath.slice(embeddedPrefixIndex + 1);
  }

  const sourceSegmentIndex = normalizedPath.lastIndexOf("/src/");
  if (sourceSegmentIndex >= 0) {
    return `${normalizedPrefix}${normalizedPath.slice(sourceSegmentIndex)}`;
  }

  return `${normalizedPrefix}/${normalizedPath}`;
}

/**
 * Re-anchor an istanbul file-coverage object's ``path`` under the
 * supplied prefix so reports emitted to SonarCloud / Codecov / qlty
 * resolve to the correct repo-relative location.
 *
 * @param {{ path: string }} fileCoverage - istanbul fileCoverage object.
 * @param {string} prefix - Repo-relative prefix to anchor under.
 * @returns {object} A shallow copy of ``fileCoverage`` with the prefixed path.
 */
function prefixCoverageMapPath(fileCoverage, prefix) {
  return {
    ...fileCoverage,
    path: prefixCoveragePath(fileCoverage.path, prefix),
  };
}

module.exports = {
  prefixCoverageMapPath,
  prefixCoveragePath,
};
