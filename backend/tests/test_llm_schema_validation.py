import pytest
from pydantic import ValidationError

from app.domain.models import LLMFaultTreeResponse, LLMNode


def test_gate_with_probability_is_rejected():
    with pytest.raises(ValidationError):
        LLMNode(id="g", type="GATE", gate_type="OR", description="g", children_ids=["a"], probability=0.5)


def test_basic_with_gate_type_is_rejected():
    with pytest.raises(ValidationError):
        LLMNode(id="a", type="BASIC", gate_type="OR", description="a")


def test_basic_with_children_is_rejected():
    with pytest.raises(ValidationError):
        LLMNode(id="a", type="BASIC", description="a", children_ids=["b"])


def test_gate_without_gate_type_is_rejected():
    with pytest.raises(ValidationError):
        LLMNode(id="g", type="GATE", description="g", children_ids=["a"])


def test_gate_with_no_children_is_rejected():
    with pytest.raises(ValidationError):
        LLMNode(id="g", type="GATE", gate_type="OR", description="g", children_ids=[])


def test_duplicate_node_ids_rejected():
    a = LLMNode(id="a", type="BASIC", description="a")
    with pytest.raises(ValidationError):
        LLMFaultTreeResponse(top_event_id="a", nodes=[a, a])


def test_dangling_child_reference_rejected():
    top = LLMNode(id="top", type="GATE", gate_type="OR", description="top", children_ids=["missing"])
    with pytest.raises(ValidationError):
        LLMFaultTreeResponse(top_event_id="top", nodes=[top])


def test_unknown_top_event_id_rejected():
    a = LLMNode(id="a", type="BASIC", description="a")
    with pytest.raises(ValidationError):
        LLMFaultTreeResponse(top_event_id="nonexistent", nodes=[a])
