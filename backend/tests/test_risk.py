import math

from app.domain.models import LossMagnitude, ProbabilityResult
from app.domain.risk import compute_risk_quantification


def prob(p):
    return ProbabilityResult(top_event_probability=p, method="exact" if p is not None else "unavailable")


def test_ale_baseline_and_residual_and_savings():
    loss = LossMagnitude(amount=1_000_000)
    rq = compute_risk_quantification(loss, prob(0.1), prob(0.02))
    assert math.isclose(rq.baseline_ale, 100_000)
    assert math.isclose(rq.residual_ale, 20_000)
    assert math.isclose(rq.savings, 80_000)


def test_none_propagates_when_probability_unavailable():
    loss = LossMagnitude(amount=1_000_000)
    rq = compute_risk_quantification(loss, prob(None), prob(0.02))
    assert rq.baseline_ale is None
    assert rq.savings is None
    assert math.isclose(rq.residual_ale, 20_000)
