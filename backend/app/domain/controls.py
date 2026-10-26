"""Applies control effectiveness to basic-event probabilities to produce a residual
probability lookup, used to compute the "with controls" (residual) view alongside the
"as authored" (baseline) view.

residual_probability(event) = base_probability * product(1 - effectiveness) over all
*active* controls targeting that event. A control whose target_basic_event_id does not
match any basic event currently in the tree is kept (in case the user re-adds that
event later) but reported as unmatched via a warning.
"""

from __future__ import annotations

from app.domain.models import BasicEvent, Control, Gate


def _collect_basic_event_ids(node: Gate | BasicEvent) -> set[str]:
    if isinstance(node, BasicEvent):
        return {node.id}
    ids: set[str] = set()
    for c in node.children:
        ids |= _collect_basic_event_ids(c)
    return ids


def _collect_baseline(node: Gate | BasicEvent, lookup: dict[str, float | None]) -> None:
    if isinstance(node, BasicEvent):
        lookup[node.id] = node.probability
        return
    for c in node.children:
        _collect_baseline(c, lookup)


def build_probability_lookups(
    root: Gate, controls: list[Control]
) -> tuple[dict[str, float | None], dict[str, float | None], list[str]]:
    """Returns (baseline_lookup, residual_lookup, warnings)."""
    baseline: dict[str, float | None] = {}
    _collect_baseline(root, baseline)

    residual: dict[str, float | None] = dict(baseline)
    for event_id, base_p in baseline.items():
        if base_p is None:
            continue
        multiplier = 1.0
        for control in controls:
            if control.active and control.target_basic_event_id == event_id:
                multiplier *= 1.0 - control.effectiveness
        residual[event_id] = base_p * multiplier

    tree_ids = _collect_basic_event_ids(root)
    unmatched = sorted({c.target_basic_event_id for c in controls if c.target_basic_event_id not in tree_ids})

    warnings: list[str] = []
    if unmatched:
        warnings.append(
            "Control(s) targeting basic event id(s) "
            + ", ".join(unmatched)
            + " do not match any basic event currently in the tree and have no effect"
        )

    return baseline, residual, warnings
