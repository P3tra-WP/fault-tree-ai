"""Minimal cut-set computation via bottom-up Boolean expansion.

BASIC -> {frozenset({id})}
OR    -> union of children's cutset sets (any one child's failure suffices)
AND   -> cartesian product of children's cutset sets, unioning each combination
         (all children must fail together)

Then minimize by absorption: drop any candidate that is a (non-strict) superset of an
already-accepted, smaller cut set.
"""

from __future__ import annotations

from app.domain.models import BasicEvent, Gate

MAX_CUTSET_COMBINATIONS = 100_000


def _cutsets(node: Gate | BasicEvent, warnings: list[str]) -> set[frozenset[str]]:
    if isinstance(node, BasicEvent):
        return {frozenset({node.id})}

    child_sets = [_cutsets(c, warnings) for c in node.children]

    if node.gate_type == "OR":
        result: set[frozenset[str]] = set()
        for cs in child_sets:
            result |= cs
        return result

    # AND gate: cartesian product across children, unioning each combination.
    combo_count = 1
    for cs in child_sets:
        combo_count *= max(len(cs), 1)

    if combo_count > MAX_CUTSET_COMBINATIONS:
        warnings.append(
            f"Cut-set computation truncated at gate {node.id!r}: AND fan-in produced "
            f"too many combinations ({combo_count} > {MAX_CUTSET_COMBINATIONS}) for exact "
            "enumeration. Falling back to a coarse approximation for this branch."
        )
        merged: frozenset[str] = frozenset()
        for cs in child_sets:
            merged |= min(cs, key=len)
        return {merged}

    result = {frozenset()}
    for cs in child_sets:
        result = {a | b for a in result for b in cs}
    return result


def _minimize(cutsets: set[frozenset[str]]) -> list[frozenset[str]]:
    ordered = sorted(cutsets, key=len)
    minimal: list[frozenset[str]] = []
    for candidate in ordered:
        if not any(accepted <= candidate for accepted in minimal):
            minimal.append(candidate)
    return minimal


def compute_minimal_cutsets(root: Gate) -> tuple[list[frozenset[str]], list[str]]:
    warnings: list[str] = []
    all_sets = _cutsets(root, warnings)
    return _minimize(all_sets), warnings
