import pytest

from app.domain.models import LLMFaultTreeResponse, LLMNode
from app.domain.tree_builder import build_fault_tree
from app.domain.tree_validation import TreeValidationError


def gate(id_, gate_type, children):
    return LLMNode(id=id_, type="GATE", gate_type=gate_type, description=id_, children_ids=children)


def leaf(id_, probability=None):
    return LLMNode(id=id_, type="BASIC", description=id_, probability=probability)


def test_valid_flat_response_builds_correct_nested_tree():
    response = LLMFaultTreeResponse(
        top_event_id="top",
        nodes=[gate("top", "OR", ["a", "b"]), leaf("a", 0.1), leaf("b", 0.2)],
    )
    tree, warnings = build_fault_tree(response, "disaster")
    assert warnings == []
    assert tree.root.id == "top"
    assert tree.root.gate_type == "OR"
    assert {c.id for c in tree.root.children} == {"a", "b"}


def test_cycle_raises():
    response = LLMFaultTreeResponse(
        top_event_id="top",
        nodes=[gate("top", "OR", ["g2"]), gate("g2", "OR", ["top"])],
    )
    with pytest.raises(TreeValidationError):
        build_fault_tree(response, "disaster")


def test_shared_gate_raises():
    # g2 referenced as a child by both `top` and `other` -> DAG, not a tree.
    response = LLMFaultTreeResponse(
        top_event_id="top",
        nodes=[
            gate("top", "OR", ["g2", "other"]),
            gate("other", "OR", ["g2"]),
            gate("g2", "OR", ["a"]),
            leaf("a"),
        ],
    )
    with pytest.raises(TreeValidationError):
        build_fault_tree(response, "disaster")


def test_repeated_basic_event_id_is_accepted():
    response = LLMFaultTreeResponse(
        top_event_id="top",
        nodes=[
            gate("top", "OR", ["g1", "g2"]),
            gate("g1", "AND", ["a", "shared"]),
            gate("g2", "AND", ["b", "shared"]),
            leaf("a"),
            leaf("b"),
            leaf("shared"),
        ],
    )
    tree, warnings = build_fault_tree(response, "disaster")
    assert warnings == []
    shared_ids = [c.id for g in tree.root.children for c in g.children if c.id == "shared"]
    assert len(shared_ids) == 2


def test_unreachable_node_produces_warning_not_error():
    response = LLMFaultTreeResponse(
        top_event_id="top",
        nodes=[gate("top", "OR", ["a"]), leaf("a"), leaf("orphan")],
    )
    tree, warnings = build_fault_tree(response, "disaster")
    assert len(warnings) == 1
    assert "orphan" in warnings[0]
