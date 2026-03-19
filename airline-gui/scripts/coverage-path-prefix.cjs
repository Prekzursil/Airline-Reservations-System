function prefixCoveragePath(filePath, prefix) {
  const normalizedPrefix = prefix.replaceAll("\\", "/").replace(/\/+$/, "");
  const normalizedPath = filePath.replaceAll("\\", "/").replace(/^(?:\.\/)+/, "");

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
