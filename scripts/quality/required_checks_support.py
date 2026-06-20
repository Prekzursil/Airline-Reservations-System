"""Evaluation helpers for required GitHub check contexts."""

from __future__ import absolute_import, annotations, division

from typing import Dict, List, Optional, Tuple


def _evaluate_check_run(
    context: str,
    observed: Dict[str, str],
) -> Optional[str]:
    """Return a failure description for an incomplete check run."""
    state = observed.get("state")
    conclusion = observed.get("conclusion")
    if state != "completed":
        return f"{context}: status={state}"
    if conclusion != "success":
        return f"{context}: conclusion={conclusion}"
    return None


def _evaluate_status_context(
    context: str,
    observed: Dict[str, str],
) -> Optional[str]:
    """Return a failure description for a non-success status."""
    state = observed.get("conclusion")
    if state != "success":
        return f"{context}: state={state}"
    return None


def evaluate_required_contexts(
    required: List[str],
    contexts: Dict[str, Dict[str, str]],
) -> Tuple[str, List[str], List[str]]:
    """Evaluate required contexts and return status with details."""
    missing: List[str] = []
    failed: List[str] = []

    for context in required:
        observed = contexts.get(context)
        if not observed:
            missing.append(context)
            continue
        evaluator = (
            _evaluate_check_run
            if observed.get("source") == "check_run"
            else _evaluate_status_context
        )
        failure = evaluator(context, observed)
        if failure:
            failed.append(failure)

    status = "pass" if not missing and not failed else "fail"
    return status, missing, failed


def has_check_runs_in_progress(
    contexts: Dict[str, Dict[str, str]],
) -> bool:
    """Return whether any check run is still in progress."""
    return any(
        observed.get("source") == "check_run" and observed.get("state") != "completed"
        for observed in contexts.values()
    )
