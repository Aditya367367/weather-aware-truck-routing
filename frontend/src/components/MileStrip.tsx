import type { RouteSummary } from "../api/types";
import { RISK } from "../lib/risk";

/** The route's miles by risk level, as one proportional strip. */
export function MileStrip({ summary, total }: { summary: RouteSummary; total: number }) {
  const miles = [summary.low_miles, summary.moderate_miles, summary.high_miles, summary.severe_miles, summary.no_travel_miles];
  const description = RISK.map((r, i) => `${Math.round(miles[i])} miles ${r.label}`).join(", ");
  return (
    <div className="mile-strip" role="img" aria-label={description} title={description}>
      {miles.map((m, i) =>
        m > 0 ? <span key={RISK[i].level} style={{ flexGrow: m / total, background: RISK[i].color }} /> : null,
      )}
    </div>
  );
}
