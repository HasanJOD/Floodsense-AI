import { classProbBar, RISK_BANDS } from '../format';
import type { FloodProbabilityResponse, RiskBand } from '../types';

export default function ClassBreakdown({ data }: { data: FloodProbabilityResponse }) {
  const maxBar = 25;
  const probs = data.class_probabilities;

  return (
    <div className="rounded-lg border border-flood-border bg-flood-panel p-6">
      <h3 className="mb-4 text-sm font-semibold text-flood-text">
        Risk Class Breakdown
      </h3>
      <div className="space-y-1">
        {RISK_BANDS.map((band) => {
          const value =
            band === 'LOW'
              ? 100 - data.flood_probability
              : probs[band as RiskBand] ?? 0;
          return (
            <div key={band}>
              {classProbBar(
                band as RiskBand,
                value,
                band === 'LOW' ? 100 : maxBar,
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
