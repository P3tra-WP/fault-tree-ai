import pytest

from app.domain.models import BasicEvent, FaultTree, Gate, TopEvent
from app.domain.tree_validation import TreeValidationError, validate_fault_tree


def basic(id_: str) -> BasicEvent:
    return BasicEvent(id=id_, description=id_)


def test_valid_tree_has_no_warnings():
    tree = FaultTree(
        top_event=TopEvent(description="disaster"),
        root=Gate(id="top", gate_type="OR", description="top", children=[basic("a"), basic("b")]),
    )
    assert validate_fault_tree(tree) == []


def test_duplicate_gate_id_raises():
    tree = FaultTree(
        top_event=TopEvent(description="disaster"),
        root=Gate(
            id="top",
            gate_type="OR",
            description="top",
            children=[
                Gate(id="dup", gate_type="AND", description="g1", children=[basic("a")]),
                Gate(id="dup", gate_type="AND", description="g2", children=[basic("b")]),
            ],
        ),
    )
    with pytest.raises(TreeValidationError):
        validate_fault_tree(tree)


def test_repeated_basic_event_id_produces_warning_not_error():
    tree = FaultTree(
        top_event=TopEvent(description="disaster"),
        root=Gate(id="top", gate_type="OR", description="top", children=[basic("a"), basic("a")]),
    )
    warnings = validate_fault_tree(tree)
    assert len(warnings) == 1
    assert "a" in warnings[0]


def test_gate_with_no_children_raises():
    # Pydantic allows constructing an empty children list; validation must catch it.
    tree = FaultTree(
        top_event=TopEvent(description="disaster"),
        root=Gate(id="top", gate_type="OR", description="top", children=[]),
    )
    with pytest.raises(TreeValidationError):
        validate_fault_tree(tree)
