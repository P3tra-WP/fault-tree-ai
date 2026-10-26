import type { CutSet } from "../types";

function fmtProb(p: number | null): string {
  return p === null ? "unavailable" : `${(p * 100).toFixed(2)}%`;
}

interface CutSetsListProps {
  cutSets: CutSet[];
  showResidual: boolean;
}

export function CutSetsList({ cutSets, showResidual }: CutSetsListProps) {
  return (
    <div className="cutsets-list">
      <h3>Minimal Cut Sets</h3>
      {cutSets.length === 0 ? (
        <p className="muted">No cut sets computed yet.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Events</th>
              <th>Baseline P</th>
              {showResidual && <th>Residual P</th>}
            </tr>
          </thead>
          <tbody>
            {cutSets.map((cs, i) => (
              <tr key={i}>
                <td>{cs.event_descriptions.join(", ")}</td>
                <td>{fmtProb(cs.baseline_probability)}</td>
                {showResidual && <td>{fmtProb(cs.residual_probability)}</td>}
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
