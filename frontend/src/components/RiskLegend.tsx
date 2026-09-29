import { bandColor } from '../format';
import { RISK_BANDS } from '../format';

export default function RiskLegend() {
  return (
    <div className="absolute left-4 bottom-4 z-[1000] rounded-md border border-flood-border bg-flood-panel/90 px-3 py-2 text-xs text-flood-muted backdrop-blur-sm">
      <div className="mb-1 font-medium text-flood-text">Risk Legend</div>
      <div className="flex flex-col gap-1">
        {RISK_BANDS.map((band) => (
          <div key={band} className="flex items-center gap-2">
            <span
              className="h-3 w-3 rounded-full"
              style={{ backgroundColor: bandColor(band) }}
            />
            <span>{band}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
