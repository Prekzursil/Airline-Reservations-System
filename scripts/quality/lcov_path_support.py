"""Path normalization helpers shared by LCOV quality scripts."""

from __future__ import absolute_import, annotations, division

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Dict, List

_SOURCE_SUFFIXES = (
    ".cpp",
    ".h",
    ".hpp",
    ".c",
    ".cc",
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
)


@dataclass(frozen=True)
class RepoFileIndexes:
    """Repository-relative lookup indexes used for LCOV path normalization."""

    repo_root: Path
    by_name: Dict[str, List[str]]
    casefold_paths: Dict[str, str]


def trim_to_source_suffix(raw_path: str) -> str:
    """Trim known LCOV suffix noise after a source filename."""
    normalized = (raw_path or "").replace("\\", "/")
    best_match = ""
    for suffix in _SOURCE_SUFFIXES:
        index = normalized.casefold().find(suffix)
        if index == -1:
            continue
        candidate = normalized[: index + len(suffix)]
        if len(candidate) > len(best_match):
            best_match = candidate
    return best_match or normalized


def sanitize_relative_candidate(raw_path: str) -> str:
    """Normalize relative path prefixes into a stable candidate value."""
    candidate = trim_to_source_suffix(raw_path).replace("\\", "/").strip()
    while candidate.startswith("./"):
        candidate = candidate[2:]
    while candidate.startswith("../"):
        candidate = candidate[3:]
    return candidate


def build_repo_file_indexes(repo_root: Path) -> RepoFileIndexes:
    """Index repository files by basename and casefolded relative path."""
    by_name: Dict[str, List[str]] = {}
    casefold_paths: Dict[str, str] = {}
    resolved_root = repo_root.resolve(strict=False)

    for path in resolved_root.rglob("*"):
        try:
            if not path.is_file():
                continue
        except OSError:
            continue

        relative = path.relative_to(resolved_root).as_posix()
        casefold_paths[relative.casefold()] = relative
        by_name.setdefault(path.name, []).append(relative)

    return RepoFileIndexes(
        repo_root=resolved_root,
        by_name=by_name,
        casefold_paths=casefold_paths,
    )


def matching_repo_suffix(raw_path: str, casefold_paths: Dict[str, str]) -> str:
    """Return the best-matching repository suffix for an arbitrary input path."""
    candidate = sanitize_relative_candidate(raw_path)
    candidate_casefold = candidate.casefold()
    if candidate_casefold in casefold_paths:
        return casefold_paths[candidate_casefold]

    best_match = ""
    for casefold_path, canonical in casefold_paths.items():
        if (
            candidate_casefold.endswith(casefold_path)
            and len(canonical) > len(best_match)
        ):
            best_match = canonical
    return best_match or candidate


def normalize_source_path(
    raw_path: str,
    *,
    repo_indexes: RepoFileIndexes,
) -> str:
    """Normalize LCOV source-file paths to repository-relative paths when possible."""
    candidate = (raw_path or "").replace("\\", "/").strip()
    if not candidate:
        return ""

    repo_root = repo_indexes.repo_root.as_posix().rstrip("/")
    if candidate == repo_root:
        return ""
    if candidate.startswith(repo_root + "/"):
        candidate = candidate[len(repo_root) + 1:]

    matched = matching_repo_suffix(candidate, repo_indexes.casefold_paths)
    if matched.casefold() in repo_indexes.casefold_paths:
        return repo_indexes.casefold_paths[matched.casefold()]

    basename = PurePosixPath(matched).name
    basename_matches = repo_indexes.by_name.get(basename) or []
    if len(basename_matches) == 1:
        return basename_matches[0]

    return matched
