"""GitHub commit-context collection helpers for quality gates."""

from __future__ import absolute_import, annotations, division

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional


@dataclass(frozen=True)
class ContextSourceSpec:
    """Mapping rules for extracting context entries from a payload."""

    name_field: str
    state_field: str
    conclusion_field: Optional[str]
    source: str


CHECK_RUN_SPEC = ContextSourceSpec(
    name_field="name",
    state_field="status",
    conclusion_field="conclusion",
    source="check_run",
)

STATUS_SPEC = ContextSourceSpec(
    name_field="context",
    state_field="state",
    conclusion_field=None,
    source="status",
)


def _context_name(value: Any) -> str:
    """Normalize a context name to a stripped string."""
    return str(value or "").strip()


def _build_context_entry(
    *,
    state: Any,
    conclusion: Any,
    source: str,
) -> Dict[str, str]:
    """Build a normalized context entry dictionary."""
    return {
        "state": str(state or ""),
        "conclusion": str(conclusion or ""),
        "source": source,
    }


def collect_context_entries(
    items: Iterable[Any],
    spec: ContextSourceSpec,
) -> Dict[str, Dict[str, str]]:
    """Extract named context entries from a payload."""
    contexts: Dict[str, Dict[str, str]] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        name = _context_name(item.get(spec.name_field))
        if not name:
            continue
        state = item.get(spec.state_field)
        conclusion = (
            state if spec.conclusion_field is None else item.get(spec.conclusion_field)
        )
        contexts[name] = _build_context_entry(
            state=state,
            conclusion=conclusion,
            source=spec.source,
        )
    return contexts


def collect_contexts(
    check_runs_payload: Dict[str, Any],
    status_payload: Dict[str, Any],
) -> Dict[str, Dict[str, str]]:
    """Merge check-run and status contexts into one map."""
    check_runs = check_runs_payload.get("check_runs", []) or []
    contexts = collect_context_entries(
        check_runs,
        CHECK_RUN_SPEC,
    )
    statuses = status_payload.get("statuses", []) or []
    contexts.update(
        collect_context_entries(statuses, STATUS_SPEC),
    )
    return contexts
