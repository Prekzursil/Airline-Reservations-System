function trimTrailingSlashes(value) {
  let normalizedValue = value;
  while (normalizedValue.endsWith("/")) {
    normalizedValue = normalizedValue.slice(0, -1);
  }
  return normalizedValue;
}

function trimLeadingCurrentDirectory(value) {
  let normalizedValue = value;
  while (normalizedValue.startsWith("./")) {
    normalizedValue = normalizedValue.slice(2);
  }
  return normalizedValue;
}

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
