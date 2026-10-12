import type { Checkpoint } from "../api/types";
import { formatTime } from "../lib/format";
import { RISK, riskColor } from "../lib/risk";

interface Props {
  checkpoints: Checkpoint[];
  onFocus: (c: Checkpoint) => void;
}

export function CheckpointTable({ checkpoints, onFocus }: Props) {
  return (
    <div className="table-wrap" tabIndex={0} role="region" aria-label="Checkpoints for the selected route">
      <table>
        <thead>
          <tr>
            <th>Mile</th>
            <th>ETA</th>
            <th>Risk</th>
            <th>Wind</th>
            <th>Rain</th>
            <th>Snow</th>
          </tr>
        </thead>
        <tbody>
          {checkpoints.map((c) => (
            <tr key={c.index} onClick={() => onFocus(c)}>
              <td>{Math.round(c.mile)}</td>
              <td>{formatTime(c.eta)}</td>
              <td>
                <span className="dot" style={{ background: riskColor(c.level) }} />
                {RISK[c.level].label}
                {c.load_adjusted && <abbr title="Raised by the load-weight rule"> (load)</abbr>}
              </td>
              <td>{c.wind_mph} mph</td>
              <td>{c.rain_in_hr} in/hr</td>
              <td>{c.snow_in_hr} in/hr</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
