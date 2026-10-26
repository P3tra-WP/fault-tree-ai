"""Bottom-up probability propagation, plus assembly of CutSet models annotated with
baseline/residual probabilities.

OR gate:  1 - product(1 - p_child)
AND gate: product(p_child)

This recursion is exact only if every basic-event id is unique across the tree (no
shared leaves) -- treating branches as independent would otherwise double-count a
shared root cause. When a basic event id repeats, we fall back to the standard FTA
rare-event approximation over the minimal cut sets: P(top) ~= sum_cutsets(product(p_i)).

If any leaf lacks a probability at all, the top event probability is reported as
"unavailable", with a warning listing which basic events need estimates.
"""

from __future__ import annotations

from app.domain.models import BasicEvent, CutSet, Gate, ProbabilityResult


def _collect_basic_events(node: Gate | BasicEvent) -> list[BasicEvent]:
    if isinstance(node, BasicEvent):
        return [node]
    events: list[BasicEvent] = []
    for c in node.children:
        events.extend(_collect_basic_events(c))
    return events


def _propagate(node: Gate | BasicEvent, prob_lookup: dict[str, float | None]) -> float | None:
    if isinstance(node, BasicEvent):
        return prob_lookup.get(node.id)

    child_probs = [_propagate(c, prob_lookup) for c in node.children]
    if any(p is None for p in child_probs):
        return None

    if node.gate_type == "OR":
        acc = 1.0
        for p in child_probs:
            acc *= 1.0 - p
        return 1.0 - acc

    acc = 1.0
    for p in child_probs:
        acc *= p
    return acc


def _rare_event_approximation(
    cutsets: list[frozenset[str]], prob_lookup: dict[str, float | None]
) -> float | None:
    total = 0.0
    for cs in cutsets:
        probs = [prob_lookup.get(eid) for eid in cs]
        if any(p is None for p in probs):
            return None
        combo = 1.0
        for p in probs:
            combo *= p
        total += combo
    return total


def compute_probability(
    root: Gate,
    cutsets: list[frozenset[str]],
    prob_lookup: dict[str, float | None],
) -> ProbabilityResult:
    all_events = _collect_basic_events(root)
    ids = [e.id for e in all_events]
    has_duplicates = len(ids) != len(set(ids))
    missing = sorted({e.id for e in all_events if prob_lookup.get(e.id) is None})

    if missing:
        return ProbabilityResult(
            top_event_probability=None,
            method="unavailable",
            warnings=["Missing probability estimate for basic event(s): " + ", ".join(missing)],
        )

    if has_duplicates:
        p = _rare_event_approximation(cutsets, prob_lookup)
        return ProbabilityResult(
            top_event_probability=p,
            method="approximate_rare_event",
            warnings=[
                "One or more basic events appear in multiple branches; top event "
                "probability uses the standard FTA rare-event approximation over "
                "minimal cut sets rather than exact propagation."
            ],
        )

    p = _propagate(root, prob_lookup)
    return ProbabilityResult(top_event_probability=p, method="exact", warnings=[])


def build_cut_set_models(
    cutsets: list[frozenset[str]],
    root: Gate,
    baseline_lookup: dict[str, float | None],
    residual_lookup: dict[str, float | None],
) -> list[CutSet]:
    description_by_id = {e.id: e.description for e in _collect_basic_events(root)}

    def combo_prob(cs: frozenset[str], lookup: dict[str, float | None]) -> float | None:
        probs = [lookup.get(eid) for eid in cs]
        if any(p is None for p in probs):
            return None
        acc = 1.0
        for p in probs:
            acc *= p
        return acc

    models: list[CutSet] = []
    for cs in cutsets:
        ids = sorted(cs)
        models.append(
            CutSet(
                event_ids=ids,
                event_descriptions=[description_by_id.get(i, i) for i in ids],
                baseline_probability=combo_prob(cs, baseline_lookup),
                residual_probability=combo_prob(cs, residual_lookup),
            )
        )

    def sort_key(cs: CutSet) -> tuple[int, float]:
        # Known probabilities first (highest risk first); unknown last; ties broken by
        # smaller cut set size (fewer events to break = cheaper to test/control).
        if cs.baseline_probability is not None:
            return (0, -cs.baseline_probability)
        return (1, len(cs.event_ids))

    models.sort(key=sort_key)
    return models
