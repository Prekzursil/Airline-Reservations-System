from __future__ import absolute_import, annotations, division

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional


@dataclass(frozen=True)
class ContextSourceSpec:
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
    return str(value or "").strip()


def _build_context_entry(*, state: Any, conclusion: Any, source: str) -> Dict[str, str]:
    return {
        "state": str(state or ""),
        "conclusion": str(conclusion or ""),
        "source": source,
    }


def collect_context_entries(items: Iterable[Any], spec: ContextSourceSpec) -> Dict[str, Dict[str, str]]:
    contexts: Dict[str, Dict[str, str]] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        name = _context_name(item.get(spec.name_field))
        if not name:
            continue
        state = item.get(spec.state_field)
        conclusion = state if spec.conclusion_field is None else item.get(spec.conclusion_field)
        contexts[name] = _build_context_entry(state=state, conclusion=conclusion, source=spec.source)
    return contexts


def collect_contexts(check_runs_payload: Dict[str, Any], status_payload: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    contexts = collect_context_entries(check_runs_payload.get("check_runs", []) or [], CHECK_RUN_SPEC)
    contexts.update(collect_context_entries(status_payload.get("statuses", []) or [], STATUS_SPEC))
    return contexts
