"""Import a previously-exported fault tree: either replace the current tree outright,
or merge it in as a new subtree under a chosen gate in the current tree.

Merge namespaces every id in the imported tree with a fresh prefix so it can never
collide with ids already in the current tree (or with a previous import), then appends
the imported root as a new child of the target gate. Attaching under an OR gate is
semantically clean (a new alternative path); attaching under an AND gate changes what
that AND requires, which is allowed but surfaced as a warning so the user consciously
accepts the change rather than it happening silently.
"""

from __future__ import annotations

from app.domain.models import BasicEvent, FaultTree, Gate
from app.domain.tree_validation import TreeValidationError


def _namespace(node: Gate | BasicEvent, prefix: str) -> Gate | BasicEvent:
    if isinstance(node, BasicEvent):
        return node.model_copy(update={"id": f"{prefix}{node.id}"})
    return node.model_copy(
        update={
            "id": f"{prefix}{node.id}",
            "children": [_namespace(c, prefix) for c in node.children],
        }
    )


def _find_gate(node: Gate | BasicEvent, gate_id: str) -> Gate | None:
    if isinstance(node, BasicEvent):
        return None
    if node.id == gate_id:
        return node
    for c in node.children:
        found = _find_gate(c, gate_id)
        if found is not None:
            return found
    return None


def import_fault_tree(
    current_tree: FaultTree | None,
    imported_tree: FaultTree,
    mode: str,
    attach_gate_id: str | None,
    import_sequence: int,
) -> tuple[FaultTree, list[str]]:
    warnings: list[str] = []

    if mode == "replace" or current_tree is None:
        return imported_tree, warnings

    if mode != "merge":
        raise TreeValidationError(f"Unknown import mode: {mode!r}")
    if not attach_gate_id:
        raise TreeValidationError("attach_gate_id is required for merge mode")

    prefix = f"imp{import_sequence}_"
    namespaced_root = _namespace(imported_tree.root, prefix)
    assert isinstance(namespaced_root, Gate)  # a FaultTree's root is always a Gate

    # Deep-copy so we never mutate the caller's in-memory tree in place.
    merged = current_tree.model_copy(deep=True)
    target = _find_gate(merged.root, attach_gate_id)
    if target is None:
        raise TreeValidationError(f"No gate with id {attach_gate_id!r} found in the current tree")

    if target.gate_type == "AND":
        warnings.append(
            f"Attached the imported tree under AND gate {attach_gate_id!r}: this changes "
            "the meaning of that gate -- it now also requires the imported subtree's "
            "condition to hold."
        )

    target.children.append(namespaced_root)
    return merged, warnings
