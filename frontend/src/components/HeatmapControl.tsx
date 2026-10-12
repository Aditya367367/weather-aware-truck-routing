import { formatTime } from "../lib/format";
import { RISK } from "../lib/risk";

interface Props {
  hour: number;
  maxHour: number;
  departure: string;
  visible: boolean;
  onHour: (h: number) => void;
  onVisible: (v: boolean) => void;
}

export function HeatmapControl({ hour, maxHour, departure, visible, onHour, onVisible }: Props) {
  const at = new Date(new Date(departure).getTime() + hour * 3_600_000);
  return (
    <section className="heat-control" aria-label="Weather heatmap">
      <div className="heat-top">
        <label className="toggle">
          <input type="checkbox" checked={visible} onChange={(e) => onVisible(e.target.checked)} />
          Weather heatmap
        </label>
        <output htmlFor="hour">
          {hour === 0 ? "At departure" : `+${hour} h`}, {formatTime(at)}
        </output>
      </div>
      <input
        id="hour"
        type="range"
        min={0}
        max={maxHour}
        step={1}
        value={hour}
        disabled={!visible}
        aria-label="Forecast hour after departure"
        onChange={(e) => onHour(Number(e.target.value))}
      />
      <div className="ticks" aria-hidden>
        {[0, 12, 24, 36, 48].map((h) => (
          <span key={h}>{h} h</span>
        ))}
      </div>
      <ul className="legend" aria-label="Risk legend">
        {RISK.map((r) => (
          <li key={r.level}>
            <span className="dot" style={{ background: r.color }} />
            {r.label}
          </li>
        ))}
      </ul>
    </section>
  );
}
