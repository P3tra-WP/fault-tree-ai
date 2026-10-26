import math

from app.domain.controls import build_probability_lookups
from app.domain.models import BasicEvent, Control, Gate


def basic(id_: str, p: float | None) -> BasicEvent:
    return BasicEvent(id=id_, description=id_, probability=p)


def make_root():
    return Gate(id="top", gate_type="OR", description="top", children=[basic("a", 0.5), basic("b", 0.2)])


def test_no_controls_residual_equals_baseline():
    root = make_root()
    baseline, residual, warnings = build_probability_lookups(root, [])
    assert baseline == residual == {"a": 0.5, "b": 0.2}
    assert warnings == []


def test_single_active_control_reduces_probability():
    root = make_root()
    controls = [Control(id="c1", description="MFA", target_basic_event_id="a", effectiveness=0.5)]
    baseline, residual, _ = build_probability_lookups(root, controls)
    assert baseline["a"] == 0.5
    assert math.isclose(residual["a"], 0.25)
    assert residual["b"] == 0.2  # untouched


def test_multiple_controls_on_same_event_compound_multiplicatively():
    root = make_root()
    controls = [
        Control(id="c1", description="c1", target_basic_event_id="a", effectiveness=0.5),
        Control(id="c2", description="c2", target_basic_event_id="a", effectiveness=0.5),
    ]
    _, residual, _ = build_probability_lookups(root, controls)
    assert math.isclose(residual["a"], 0.5 * 0.5 * 0.5)


def test_inactive_control_is_ignored():
    root = make_root()
    controls = [
        Control(id="c1", description="c1", target_basic_event_id="a", effectiveness=0.9, active=False)
    ]
    _, residual, _ = build_probability_lookups(root, controls)
    assert residual["a"] == 0.5


def test_zero_and_full_effectiveness_edge_cases():
    root = make_root()
    controls = [
        Control(id="c0", description="no-op", target_basic_event_id="a", effectiveness=0.0),
        Control(id="c1", description="perfect", target_basic_event_id="b", effectiveness=1.0),
    ]
    _, residual, _ = build_probability_lookups(root, controls)
    assert residual["a"] == 0.5
    assert residual["b"] == 0.0


def test_unmatched_control_produces_warning_not_error():
    root = make_root()
    controls = [Control(id="c1", description="c1", target_basic_event_id="nonexistent", effectiveness=0.5)]
    _, residual, warnings = build_probability_lookups(root, controls)
    assert residual == {"a": 0.5, "b": 0.2}
    assert len(warnings) == 1
    assert "nonexistent" in warnings[0]
