import { useState } from "react";
import type { LossMagnitude, RiskQuantification } from "../types";

function fmtMoney(amount: number | null, currency: string): string {
  return amount === null ? "unavailable" : `${amount.toLocaleString(undefined, { maximumFractionDigits: 2 })} ${currency}`;
}

interface RiskQuantificationPanelProps {
  lossMagnitude: LossMagnitude | null;
  riskQuantification: RiskQuantification | null;
  onChange: (loss: LossMagnitude | null) => void;
}

export function RiskQuantificationPanel({ lossMagnitude, riskQuantification, onChange }: RiskQuantificationPanelProps) {
  const [amount, setAmount] = useState(lossMagnitude?.amount ?? 0);
  const [currency, setCurrency] = useState(lossMagnitude?.currency ?? "USD");
  const [timeBase, setTimeBase] = useState(lossMagnitude?.time_base ?? "annual");

  function apply() {
    onChange(amount > 0 ? { amount, currency, time_base: timeBase } : null);
  }

  return (
    <div className="risk-panel">
      <h3>Risk Quantification (FAIR-lite)</h3>
      <div className="risk-inputs">
        <label>
          Loss magnitude if the Top Event occurs
          <input type="number" min={0} value={amount} onChange={(e) => setAmount(Number(e.target.value))} />
        </label>
        <input className="currency-input" value={currency} onChange={(e) => setCurrency(e.target.value)} />
        <input className="time-base-input" value={timeBase} onChange={(e) => setTimeBase(e.target.value)} />
        <button type="button" onClick={apply}>
          Set loss magnitude
        </button>
      </div>

      {riskQuantification && (
        <div className="risk-results">
          <div>
            <span className="label">Baseline ALE</span>
            <span className="value">
              {fmtMoney(riskQuantification.baseline_ale, riskQuantification.loss_magnitude.currency)}
            </span>
          </div>
          <div>
            <span className="label">Residual ALE</span>
            <span className="value">
              {fmtMoney(riskQuantification.residual_ale, riskQuantification.loss_magnitude.currency)}
            </span>
          </div>
          <div>
            <span className="label">Savings from active controls</span>
            <span className="value">
              {fmtMoney(riskQuantification.savings, riskQuantification.loss_magnitude.currency)}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
