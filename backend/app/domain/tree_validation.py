"""Validates an already-nested FaultTree (used by the manual-edit and import paths).

Unlike the LLM flat-schema path (tree_builder.py), there is no id-reference graph to
walk here -- the tree is already a real nested Python object tree, so cycles are not
structurally representable (a JSON document cannot encode one via containment). What
*is* still possible via a raw-JSON edit or an import is: duplicate GATE ids (ambiguous
for controls/UI targeting), gates with no children, and basic events with duplicate
ids (legal in FTA -- a shared root cause -- but must be reported so the probability
engine picks the right method).
"""

from __future__ import annotations

from app.domain.models import BasicEvent, FaultTree, Gate


class TreeValidationError(Exception):
    """Raised when a fault tree fails structural validation."""


def _walk(node: Gate | BasicEvent) -> tuple[list[str], list[str]]:
    """Returns (gate_ids, basic_event_ids) encountered in this subtree."""
    if isinstance(node, BasicEvent):
        return [], [node.id]

    if not node.children:
        raise TreeValidationError(f"Gate {node.id!r} ({node.description!r}) has no children")

    gate_ids = [node.id]
    basic_ids: list[str] = []
    for child in node.children:
        g, b = _walk(child)
        gate_ids.extend(g)
        basic_ids.extend(b)
    return gate_ids, basic_ids


def validate_fault_tree(tree: FaultTree) -> list[str]:
    """Validates structural integrity, returning non-fatal warnings.

    Raises TreeValidationError for hard failures (duplicate gate ids, empty gates).
    """
    gate_ids, basic_ids = _walk(tree.root)

    seen_gates: set[str] = set()
    for gid in gate_ids:
        if gid in seen_gates:
            raise TreeValidationError(f"Duplicate gate id {gid!r} -- gate ids must be unique")
        seen_gates.add(gid)

    warnings: list[str] = []
    duplicate_basics = sorted({b for b in basic_ids if basic_ids.count(b) > 1})
    if duplicate_basics:
        warnings.append(
            "Basic event id(s) "
            + ", ".join(duplicate_basics)
            + " appear in more than one branch. This is valid FTA (a shared root cause), "
            "but the exact probability method cannot be used -- see probability method "
            "in the result."
        )
    return warnings
