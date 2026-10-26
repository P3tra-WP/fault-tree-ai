import pytest

from app.domain.merge import import_fault_tree
from app.domain.models import BasicEvent, FaultTree, Gate, TopEvent
from app.domain.tree_validation import TreeValidationError


def basic(id_: str) -> BasicEvent:
    return BasicEvent(id=id_, description=id_)


def make_tree(root_id="top") -> FaultTree:
    return FaultTree(
        top_event=TopEvent(description="disaster"),
        root=Gate(id=root_id, gate_type="OR", description="top", children=[basic("a"), basic("b")]),
    )


def test_replace_mode_returns_imported_tree_unchanged():
    current = make_tree("current-top")
    imported = make_tree("imported-top")
    merged, warnings = import_fault_tree(current, imported, mode="replace", attach_gate_id=None, import_sequence=1)
    assert merged == imported
    assert warnings == []


def test_merge_namespaces_ids_to_avoid_collisions():
    current = make_tree("top")
    imported = make_tree("top")  # deliberately colliding ids with `current`
    merged, _ = import_fault_tree(current, imported, mode="merge", attach_gate_id="top", import_sequence=1)

    all_ids = _collect_ids(merged.root)
    assert len(all_ids) == len(set(all_ids)), "merged tree must not contain duplicate ids"
    assert any(i.startswith("imp1_") for i in all_ids)


def test_merge_under_or_gate_is_silent():
    current = make_tree("top")  # top is an OR gate
    imported = make_tree("imported-top")
    merged, warnings = import_fault_tree(current, imported, mode="merge", attach_gate_id="top", import_sequence=1)
    assert warnings == []
    assert len(merged.root.children) == 3  # original a, b + imported subtree root


def test_merge_under_and_gate_warns_about_semantic_change():
    current = FaultTree(
        top_event=TopEvent(description="disaster"),
        root=Gate(id="top", gate_type="AND", description="top", children=[basic("a"), basic("b")]),
    )
    imported = make_tree("imported-top")
    merged, warnings = import_fault_tree(current, imported, mode="merge", attach_gate_id="top", import_sequence=1)
    assert len(warnings) == 1
    assert "AND" in warnings[0]


def test_merge_with_unknown_attach_gate_id_raises():
    current = make_tree("top")
    imported = make_tree("imported-top")
    with pytest.raises(TreeValidationError):
        import_fault_tree(current, imported, mode="merge", attach_gate_id="nonexistent", import_sequence=1)


def test_repeated_imports_get_distinct_prefixes():
    current = make_tree("top")
    imported = make_tree("top")
    merged1, _ = import_fault_tree(current, imported, mode="merge", attach_gate_id="top", import_sequence=1)
    merged2, _ = import_fault_tree(merged1, imported, mode="merge", attach_gate_id="top", import_sequence=2)

    all_ids = _collect_ids(merged2.root)
    assert len(all_ids) == len(set(all_ids))
    assert any(i.startswith("imp1_") for i in all_ids)
    assert any(i.startswith("imp2_") for i in all_ids)


def _collect_ids(node) -> list[str]:
    if isinstance(node, BasicEvent):
        return [node.id]
    ids = [node.id]
    for c in node.children:
        ids.extend(_collect_ids(c))
    return ids
