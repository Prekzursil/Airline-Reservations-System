function prefixCoveragePath(filePath, prefix) {
  const normalizedPath = filePath.replace(/\\/g, "/").replace(/^(\.\/)+/, "");
  return normalizedPath.startsWith(prefix) ? normalizedPath : `${prefix}${normalizedPath}`;
}

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
