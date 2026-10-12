import { useState } from "react";
import type { AnalyzeRequest, Interval, Place } from "../api/types";
import { nextHour, toLocalInput } from "../lib/format";
import { PlaceInput } from "./PlaceInput";

const INTERVALS: Interval[] = [10, 25, 50];
const MAX_WEIGHT = 80_000;

interface Props {
  busy: boolean;
  onSubmit: (request: AnalyzeRequest) => void;
}

export function TripForm({ busy, onSubmit }: Props) {
  const [origin, setOrigin] = useState<Place | null>(null);
  const [destination, setDestination] = useState<Place | null>(null);
  const [departure, setDeparture] = useState(() => toLocalInput(nextHour()));
  const [weight, setWeight] = useState("40000");
  const [intervalMiles, setIntervalMiles] = useState<Interval>(25);

  const weightNum = Number(weight);
  const weightOk = weight !== "" && Number.isInteger(weightNum) && weightNum >= 0 && weightNum <= MAX_WEIGHT;
  const departureOk = !Number.isNaN(new Date(departure).getTime());
  const valid = Boolean(origin && destination && weightOk && departureOk);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!valid || !origin || !destination) return;
    onSubmit({
      origin,
      destination,
      departure_time: new Date(departure).toISOString(),
      load_weight_lb: weightNum,
      interval_miles: intervalMiles,
    });
  };

  const swap = () => {
    setOrigin(destination);
    setDestination(origin);
  };

  return (
    <form className="trip-form" onSubmit={submit} noValidate>
      <PlaceInput label="Origin" value={origin} onChange={setOrigin} />
      <button type="button" className="swap" onClick={swap} aria-label="Swap origin and destination" title="Swap">
        ⇅
      </button>
      <PlaceInput label="Destination" value={destination} onChange={setDestination} />

      <div className="row">
        <div className="field">
          <label htmlFor="departure">Departure</label>
          <input id="departure" type="datetime-local" value={departure} onChange={(e) => setDeparture(e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="weight">Load weight (lb)</label>
          <input
            id="weight"
            inputMode="numeric"
            value={weight}
            aria-invalid={!weightOk}
            onChange={(e) => setWeight(e.target.value.replace(/[^\d]/g, ""))}
          />
          {!weightOk && <span className="hint error">Enter 0 to {MAX_WEIGHT.toLocaleString()} lb</span>}
        </div>
      </div>

      <fieldset className="segmented">
        <legend>Weather checkpoint every</legend>
        {INTERVALS.map((n) => (
          <label key={n} className={n === intervalMiles ? "on" : undefined}>
            <input type="radio" name="interval" checked={n === intervalMiles} onChange={() => setIntervalMiles(n)} />
            {n} mi
          </label>
        ))}
      </fieldset>

      <button className="primary" type="submit" disabled={!valid || busy}>
        {busy ? "Checking weather…" : "Compare routes"}
      </button>
    </form>
  );
}
