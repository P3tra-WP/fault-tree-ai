import type { ProbabilityResult } from "../types";

function fmtProb(p: number | null): string {
  return p === null ? "unavailable" : `${(p * 100).toFixed(3)}%`;
}

interface TopEventProbabilityProps {
  baseline: ProbabilityResult;
  residual: ProbabilityResult;
  showResidual: boolean;
}

export function TopEventProbability({ baseline, residual, showResidual }: TopEventProbabilityProps) {
  const warnings = [...baseline.warnings, ...(showResidual ? residual.warnings : [])];

  return (
    <div className="top-event-probability">
      <h3>Top Event Probability</h3>
      <div className="probability-row">
        <div>
          <span className="label">Baseline</span>
          <span className="value">{fmtProb(baseline.top_event_probability)}</span>
          <span className="muted">({baseline.method})</span>
        </div>
        {showResidual && (
          <div>
            <span className="label">With active controls</span>
            <span className="value">{fmtProb(residual.top_event_probability)}</span>
            <span className="muted">({residual.method})</span>
          </div>
        )}
      </div>
      {warnings.map((w, i) => (
        <p key={i} className="warning-text">
          {w}
        </p>
      ))}
    </div>
  );
}
