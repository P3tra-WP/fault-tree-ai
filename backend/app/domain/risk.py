"""FAIR-lite monetary quantification.

Annualized Loss Expectancy (ALE) = Top Event probability x Loss Magnitude. Point
estimate only -- no Monte Carlo / PERT distribution over a min/likely/max loss range.
This is a deliberate v0 scope cut (see README limitations): it directly answers "how
many dollars of annualized risk does this control remove" without the added complexity
of a full simulation.
"""

from __future__ import annotations

from app.domain.models import LossMagnitude, ProbabilityResult, RiskQuantification


def compute_risk_quantification(
    loss_magnitude: LossMagnitude,
    baseline: ProbabilityResult,
    residual: ProbabilityResult,
) -> RiskQuantification:
    baseline_ale = (
        baseline.top_event_probability * loss_magnitude.amount
        if baseline.top_event_probability is not None
        else None
    )
    residual_ale = (
        residual.top_event_probability * loss_magnitude.amount
        if residual.top_event_probability is not None
        else None
    )
    savings = (
        baseline_ale - residual_ale if baseline_ale is not None and residual_ale is not None else None
    )
    return RiskQuantification(
        loss_magnitude=loss_magnitude,
        baseline_ale=baseline_ale,
        residual_ale=residual_ale,
        savings=savings,
    )
