import maplibregl, { type GeoJSONSource, type MapLayerMouseEvent } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useEffect, useRef, useState } from "react";
import type { Analysis, Level } from "../api/types";
import { formatTime, routeName } from "../lib/format";
import { RISK, ROUTE_COLORS, riskColor } from "../lib/risk";

export interface FocusTarget {
  lng: number;
  lat: number;
  key: number; // changes on every request so repeated clicks re-fire
}

interface Props {
  analysis: Analysis | null;
  selectedId: string | null;
  hour: number;
  showHeat: boolean;
  focus: FocusTarget | null;
  onSelectRoute: (id: string) => void;
}

const EMPTY: GeoJSON.FeatureCollection = { type: "FeatureCollection", features: [] };
// OpenFreeMap: free, keyless, built for apps (OSM's own tile servers forbid app basemap use).
const STYLE_URL = "https://tiles.openfreemap.org/styles/positron";

function initLayers(map: maplibregl.Map) {
  for (const id of ["heat", "routes", "checkpoints"]) map.addSource(id, { type: "geojson", data: EMPTY });

  map.addLayer({
    id: "heat", type: "heatmap", source: "heat",
    paint: {
      "heatmap-weight": ["get", "w"],
      "heatmap-intensity": ["interpolate", ["linear"], ["zoom"], 3, 1.1, 9, 1.8],
      "heatmap-radius": ["interpolate", ["linear"], ["zoom"], 3, 26, 5, 60, 7, 130, 9, 230, 11, 300],
      "heatmap-color": [
        "interpolate", ["linear"], ["heatmap-density"],
        0, "rgba(47,158,110,0)",
        0.12, "rgba(224,176,0,0.45)",
        0.3, "#e0b000",
        0.5, "#f08a24",
        0.75, "#d7263d",
        1, "#5b1a6b",
      ],
      "heatmap-opacity": 0.7,
    },
  });
  map.addLayer({
    id: "route-casing", type: "line", source: "routes",
    layout: { "line-cap": "round", "line-join": "round", "line-sort-key": ["get", "z"] },
    paint: { "line-color": "#fff", "line-width": ["case", ["get", "selected"], 9, 7] },
  });
  map.addLayer({
    id: "route-line", type: "line", source: "routes",
    layout: { "line-cap": "round", "line-join": "round", "line-sort-key": ["get", "z"] },
    paint: {
      "line-color": ["get", "color"],
      "line-width": ["case", ["get", "selected"], 6, 4],
      "line-opacity": ["case", ["get", "selected"], 1, 0.6],
    },
  });
  map.addLayer({
    id: "checkpoints", type: "circle", source: "checkpoints",
    paint: {
      "circle-radius": ["interpolate", ["linear"], ["zoom"], 3, 4, 10, 8],
      "circle-color": ["get", "color"],
      "circle-stroke-color": "#fff",
      "circle-stroke-width": 2,
    },
  });
}

function popupContent(p: Record<string, unknown>): HTMLElement {
  const root = document.createElement("div");
  root.className = "popup";
  const title = document.createElement("strong");
  title.textContent = `Mile ${p.mile}, ${RISK[p.level as Level].label}`;
  const eta = document.createElement("div");
  eta.textContent = `ETA ${p.eta}`;
  const wx = document.createElement("div");
  wx.textContent = `Wind ${p.wind} mph, rain ${p.rain} in/hr, snow ${p.snow} in/hr`;
  root.append(title, eta, wx);
  return root;
}

export function MapView({ analysis, selectedId, hour, showHeat, focus, onSelectRoute }: Props) {
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const onSelectRef = useRef(onSelectRoute);
  const [ready, setReady] = useState(false);
  const [webglFailed, setWebglFailed] = useState(false);
  onSelectRef.current = onSelectRoute;

  // Create the map once.
  useEffect(() => {
    let map: maplibregl.Map;
    try {
      map = new maplibregl.Map({
        container: container.current!,
        style: STYLE_URL,
        center: [-98, 39],
        zoom: 3.5,
        attributionControl: { compact: true },
      });
    } catch {
      setWebglFailed(true); // no WebGL (e.g. VM without GPU): keep the rest of the app usable
      return;
    }
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    map.on("load", () => {
      initLayers(map);
      const firstLabel = map.getStyle().layers.find((l) => l.type === "symbol")?.id;
      if (firstLabel) for (const id of ["heat", "route-casing", "route-line"]) map.moveLayer(id, firstLabel);
      map.on("click", "route-line", (e: MapLayerMouseEvent) => {
        const id = e.features?.[0]?.properties?.id;
        if (id) onSelectRef.current(id);
      });
      map.on("click", "checkpoints", (e: MapLayerMouseEvent) => {
        const f = e.features?.[0];
        if (!f) return;
        new maplibregl.Popup({ offset: 12 })
          .setLngLat((f.geometry as GeoJSON.Point).coordinates as [number, number])
          .setDOMContent(popupContent(f.properties))
          .addTo(map);
      });
      for (const layer of ["route-line", "checkpoints"]) {
        map.on("mouseenter", layer, () => (map.getCanvas().style.cursor = "pointer"));
        map.on("mouseleave", layer, () => (map.getCanvas().style.cursor = ""));
      }
      mapRef.current = map;
      setReady(true);
    });
    return () => {
      map.remove();
      mapRef.current = null;
      setReady(false);
    };
  }, []);

  const setData = (source: string, data: GeoJSON.FeatureCollection) =>
    (mapRef.current?.getSource(source) as GeoJSONSource | undefined)?.setData(data);

  // Routes: redrawn on new results or selection change.
  useEffect(() => {
    if (!ready) return;
    setData("routes", {
      type: "FeatureCollection",
      features: (analysis?.routes ?? []).map((r, i) => ({
        type: "Feature",
        geometry: { type: "LineString", coordinates: r.geometry },
        properties: {
          id: r.id,
          color: ROUTE_COLORS[i % ROUTE_COLORS.length],
          selected: r.id === selectedId,
          z: r.id === selectedId ? 1 : 0,
          name: routeName(r.id),
        },
      })),
    });
  }, [ready, analysis, selectedId]);

  // Checkpoints of the selected route.
  useEffect(() => {
    if (!ready) return;
    const route = analysis?.routes.find((r) => r.id === selectedId);
    setData("checkpoints", {
      type: "FeatureCollection",
      features: (route?.checkpoints ?? []).map((c) => ({
        type: "Feature",
        geometry: { type: "Point", coordinates: [c.lng, c.lat] },
        properties: {
          level: c.level, color: riskColor(c.level), mile: Math.round(c.mile), eta: formatTime(c.eta),
          wind: c.wind_mph, rain: c.rain_in_hr, snow: c.snow_in_hr,
        },
      })),
    });
  }, [ready, analysis, selectedId]);

  // Heatmap: only the per-point weight changes with the slider.
  useEffect(() => {
    if (!ready) return;
    const points = analysis?.heatmap.points ?? [];
    setData("heat", {
      type: "FeatureCollection",
      features: points.map((p) => ({
        type: "Feature",
        geometry: { type: "Point", coordinates: [p.lng, p.lat] },
        properties: { w: p.levels[hour] / 4 },
      })),
    });
  }, [ready, analysis, hour]);

  useEffect(() => {
    if (ready) mapRef.current?.setLayoutProperty("heat", "visibility", showHeat ? "visible" : "none");
  }, [ready, showHeat]);

  // Fit the viewport when a new analysis arrives.
  useEffect(() => {
    if (!ready || !analysis) return;
    const bounds = new maplibregl.LngLatBounds();
    for (const r of analysis.routes) for (const c of r.geometry) bounds.extend(c);
    mapRef.current?.fitBounds(bounds, { padding: { top: 60, bottom: 190, left: 60, right: 60 }, duration: 900 });
  }, [ready, analysis]);

  useEffect(() => {
    const map = mapRef.current;
    if (ready && focus && map) map.easeTo({ center: [focus.lng, focus.lat], zoom: Math.max(map.getZoom(), 8.5) });
  }, [ready, focus]);

  if (webglFailed) {
    return (
      <div className="map map-fallback" role="alert">
        <p>The map needs WebGL, which this browser or machine has disabled. Enable hardware acceleration or try another browser. Route results are still listed in the side panel.</p>
      </div>
    );
  }
  return <div ref={container} className="map" />;
}
