import { useEffect, useMemo, useState } from "react";
import type { Checkpoint } from "./api/types";
import { CheckpointTable } from "./components/CheckpointTable";
import { HeatmapControl } from "./components/HeatmapControl";
import { MapView, type FocusTarget } from "./components/MapView";
import { RouteList } from "./components/RouteList";
import { TripForm } from "./components/TripForm";
import { useAnalysis } from "./hooks/useAnalysis";
import { routeName } from "./lib/format";

export function App() {
  const { status, data, error, run } = useAnalysis();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [hour, setHour] = useState(0);
  const [showHeat, setShowHeat] = useState(true);
  const [focus, setFocus] = useState<FocusTarget | null>(null);

  // Each new analysis resets selection and the forecast slider.
  useEffect(() => {
    if (data) {
      setSelectedId(data.recommended_route_id);
      setHour(0);
    }
  }, [data]);

  const selected = useMemo(() => data?.routes.find((r) => r.id === selectedId) ?? null, [data, selectedId]);
  const focusCheckpoint = (c: Checkpoint) => setFocus({ lng: c.lng, lat: c.lat, key: Date.now() });

  return (
    <div className="app">
      <aside className="panel">
        <header>
          <h1>Weather-aware routing</h1>
          <p>Pick the safest route for your load, with weather checked at your arrival time.</p>
        </header>

        <TripForm busy={status === "loading"} onSubmit={run} />

        {status === "error" && (
          <p className="notice error" role="alert">
            {error}
          </p>
        )}

        {data && selected && (
          <>
            <section className="recommendation" aria-live="polite">
              <h2>Take {routeName(data.recommended_route_id)}</h2>
              <p>{data.reason}</p>
              {data.advisory && <p className="notice error">{data.advisory}</p>}
            </section>
            <RouteList analysis={data} selectedId={selected.id} onSelect={setSelectedId} />
            <h2 className="section-title">Checkpoints on {routeName(selected.id)}</h2>
            <CheckpointTable checkpoints={selected.checkpoints} onFocus={focusCheckpoint} />
          </>
        )}

        {!data && status !== "loading" && (
          <p className="empty">Choose an origin and destination to compare three routes and see the forecast along each one.</p>
        )}
      </aside>

      <main className="stage">
        <MapView analysis={data} selectedId={selectedId} hour={hour} showHeat={showHeat} focus={focus} onSelectRoute={setSelectedId} />
        {data && (
          <HeatmapControl
            hour={hour}
            maxHour={data.heatmap.hours}
            departure={data.departure_time}
            visible={showHeat}
            onHour={setHour}
            onVisible={setShowHeat}
          />
        )}
        {status === "loading" && <div className="progress" role="progressbar" aria-label="Analyzing routes" />}
      </main>
    </div>
  );
}
