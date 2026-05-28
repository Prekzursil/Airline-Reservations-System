#!/usr/bin/env python3
"""Shared rendering and artifact helpers for quality gate scripts.

The zero-gate scripts (Codacy, Sonar, Sentry, DeepScan, coverage) all emit a
Markdown report that ends with a ``## Findings`` bullet list and then persist a
JSON payload plus the rendered Markdown to fixed artifact paths. These helpers
centralize that boilerplate so each gate only supplies its title, the
gate-specific header lines, and any extra Markdown sections.
"""

from __future__ import absolute_import, annotations, division

import json
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from scripts.security_helpers import QualityArtifact, quality_artifact_paths

# A Markdown section is a heading plus the bullet lines that belong under it.
MarkdownSection = Tuple[str, Sequence[str]]


def _render_bullets(items: Sequence[str]) -> List[str]:
    """Return bullet lines for ``items`` or a single ``- None`` placeholder."""
    if items:
        return [f"- {item}" for item in items]
    return ["- None"]


def render_findings(payload: Dict[str, Any]) -> List[str]:
    """Return the ``## Findings`` Markdown section for a gate payload."""
    findings = payload.get("findings") or []
    return ["## Findings", *_render_bullets(findings)]


def render_gate_markdown(
    *,
    title: str,
    header_lines: Sequence[str],
    payload: Dict[str, Any],
    extra_sections: Optional[Sequence[MarkdownSection]] = None,
) -> str:
    """Render a quality gate report as Markdown.

    The report starts with ``title``, follows with the gate-specific
    ``header_lines``, renders any ``extra_sections`` (heading + bullets) in
    order, and finishes with the standard ``## Findings`` list.
    """
    lines: List[str] = [f"# {title}", "", *header_lines, ""]
    for heading, items in extra_sections or ():
        lines.append(heading)
        lines.extend(_render_bullets(items))
        lines.append("")
    lines.extend(render_findings(payload))
    return "\n".join(lines) + "\n"


def write_gate_artifacts(
    artifact: QualityArtifact,
    payload: Dict[str, Any],
    render_md: Callable[[Dict[str, Any]], str],
) -> None:
    """Persist a gate ``payload`` as JSON and Markdown, echoing the Markdown.

    The JSON is written with sorted keys and a trailing newline; the Markdown is
    produced by ``render_md`` and echoed to stdout so CI logs show the report.
    """
    out_json, out_md = quality_artifact_paths(artifact)
    out_json.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    out_md.write_text(render_md(payload), encoding="utf-8")
    print(out_md.read_text(encoding="utf-8"), end="")
