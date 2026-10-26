import math

from app.domain.cutsets import compute_minimal_cutsets
from app.domain.models import BasicEvent, Gate
from app.domain.probability import compute_probability


def basic(id_: str, p: float | None) -> BasicEvent:
    return BasicEvent(id=id_, description=id_, probability=p)


def lookup_from_tree(root: Gate) -> dict[str, float | None]:
    result: dict[str, float | None] = {}

    def walk(node):
        if isinstance(node, BasicEvent):
            result[node.id] = node.probability
        else:
            for c in node.children:
                walk(c)

    walk(root)
    return result


def test_or_gate_probability_formula():
    root = Gate(id="top", gate_type="OR", description="top", children=[basic("a", 0.1), basic("b", 0.2)])
    cutsets, _ = compute_minimal_cutsets(root)
    result = compute_probability(root, cutsets, lookup_from_tree(root))
    assert result.method == "exact"
    assert math.isclose(result.top_event_probability, 1 - (1 - 0.1) * (1 - 0.2))


def test_and_gate_probability_formula():
    root = Gate(id="top", gate_type="AND", description="top", children=[basic("a", 0.1), basic("b", 0.2)])
    cutsets, _ = compute_minimal_cutsets(root)
    result = compute_probability(root, cutsets, lookup_from_tree(root))
    assert result.method == "exact"
    assert math.isclose(result.top_event_probability, 0.1 * 0.2)


def test_missing_leaf_probability_is_unavailable():
    root = Gate(id="top", gate_type="OR", description="top", children=[basic("a", 0.1), basic("b", None)])
    cutsets, _ = compute_minimal_cutsets(root)
    result = compute_probability(root, cutsets, lookup_from_tree(root))
    assert result.method == "unavailable"
    assert result.top_event_probability is None
    assert "b" in result.warnings[0]


def test_repeated_basic_event_uses_rare_event_approximation():
    # top = OR(AND(a, c), AND(b, c)) -- "c" is shared across both AND branches.
    root = Gate(
        id="top",
        gate_type="OR",
        description="top",
        children=[
            Gate(id="g1", gate_type="AND", description="g1", children=[basic("a", 0.1), basic("c", 0.5)]),
            Gate(id="g2", gate_type="AND", description="g2", children=[basic("b", 0.2), basic("c", 0.5)]),
        ],
    )
    cutsets, _ = compute_minimal_cutsets(root)
    lookup = {"a": 0.1, "b": 0.2, "c": 0.5}
    result = compute_probability(root, cutsets, lookup)
    assert result.method == "approximate_rare_event"
    # rare-event approx: sum over minimal cutsets of product(p_i) = (0.1*0.5) + (0.2*0.5)
    expected = (0.1 * 0.5) + (0.2 * 0.5)
    assert math.isclose(result.top_event_probability, expected)
