from app.domain.cutsets import compute_minimal_cutsets
from app.domain.models import BasicEvent, Gate


def basic(id_: str, p: float | None = None) -> BasicEvent:
    return BasicEvent(id=id_, description=id_, probability=p)


def test_or_of_two_basics_gives_two_singleton_cutsets():
    root = Gate(id="top", gate_type="OR", description="top", children=[basic("a"), basic("b")])
    cutsets, warnings = compute_minimal_cutsets(root)
    assert set(cutsets) == {frozenset({"a"}), frozenset({"b"})}
    assert warnings == []


def test_and_of_two_basics_gives_one_pair_cutset():
    root = Gate(id="top", gate_type="AND", description="top", children=[basic("a"), basic("b")])
    cutsets, _ = compute_minimal_cutsets(root)
    assert cutsets == [frozenset({"a", "b"})]


def test_nested_and_or_combo_matches_hand_computed_expectation():
    # top = OR(a, AND(b, c))  =>  minimal cutsets: {a}, {b, c}
    root = Gate(
        id="top",
        gate_type="OR",
        description="top",
        children=[
            basic("a"),
            Gate(id="g2", gate_type="AND", description="g2", children=[basic("b"), basic("c")]),
        ],
    )
    cutsets, _ = compute_minimal_cutsets(root)
    assert set(cutsets) == {frozenset({"a"}), frozenset({"b", "c"})}


def test_absorption_removes_supersets():
    # top = AND(OR(a, b), a)  =>  raw expansion gives {a}, {a,b} -- {a,b} must be dropped
    root = Gate(
        id="top",
        gate_type="AND",
        description="top",
        children=[
            Gate(id="g2", gate_type="OR", description="g2", children=[basic("a"), basic("b")]),
            basic("a"),
        ],
    )
    cutsets, _ = compute_minimal_cutsets(root)
    assert cutsets == [frozenset({"a"})]


def test_repeated_basic_event_id_across_branches_dedups_correctly():
    # top = OR(a, a) -- same id used twice -- should collapse to a single cutset {a}
    root = Gate(id="top", gate_type="OR", description="top", children=[basic("a"), basic("a")])
    cutsets, _ = compute_minimal_cutsets(root)
    assert cutsets == [frozenset({"a"})]


def test_wide_and_fan_in_triggers_complexity_guard_without_hanging():
    # AND of 6 OR-gates each with 10 children -> 10**6 raw combinations, over the cap.
    children = [
        Gate(
            id=f"or{i}",
            gate_type="OR",
            description=f"or{i}",
            children=[basic(f"e{i}_{j}") for j in range(10)],
        )
        for i in range(6)
    ]
    root = Gate(id="top", gate_type="AND", description="top", children=children)
    cutsets, warnings = compute_minimal_cutsets(root)
    assert len(warnings) == 1
    assert "truncated" in warnings[0]
    assert len(cutsets) >= 1
