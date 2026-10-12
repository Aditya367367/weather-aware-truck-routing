import type { CSSProperties } from "react";
import type { Analysis, Route } from "../api/types";
import { formatDuration, formatMiles, formatTime, routeName } from "../lib/format";
import { ROUTE_COLORS } from "../lib/risk";
import { MileStrip } from "./MileStrip";

interface Props {
  analysis: Analysis;
  selectedId: string;
  onSelect: (id: string) => void;
}

export function RouteList({ analysis, selectedId, onSelect }: Props) {
  const byId = new Map(analysis.routes.map((r) => [r.id, r]));
  const fastest = Math.min(...analysis.routes.map((r) => r.duration_s));

  return (
    <ul className="routes" aria-label="Route options">
      {analysis.ranking.map((id) => {
        const r = byId.get(id) as Route;
        const colorIdx = analysis.routes.findIndex((x) => x.id === id);
        const recommended = id === analysis.recommended_route_id;
        const extra = r.duration_s - fastest;
        return (
          <li key={id}>
            <button
              className={`route-card${id === selectedId ? " selected" : ""}`}
              aria-pressed={id === selectedId}
              onClick={() => onSelect(id)}
              style={{ "--route": ROUTE_COLORS[colorIdx % ROUTE_COLORS.length] } as CSSProperties}
            >
              <span className="route-head">
                <strong>{routeName(id)}</strong>
                {recommended && <span className="badge best">Recommended</span>}
                {extra === 0 && <span className="badge">Fastest</span>}
              </span>
              <span className="route-times">
                <b>{formatDuration(r.duration_s)}</b>
                <span>{formatMiles(r.distance_mi)}</span>
                <span>Arrive {formatTime(r.arrival)}</span>
                {extra > 0 && <span className="muted">+{formatDuration(extra)} vs fastest</span>}
              </span>
              <MileStrip summary={r.summary} total={r.distance_mi} />
              <span className="route-risk">
                <span className={r.summary.no_travel_miles ? "alert" : ""}>No Travel {formatMiles(r.summary.no_travel_miles)}</span>
                <span>Severe {formatMiles(r.summary.severe_miles)}</span>
                <span>High {formatMiles(r.summary.high_miles)}</span>
                <span>Avg risk {r.summary.avg_risk.toFixed(2)}/4</span>
              </span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
