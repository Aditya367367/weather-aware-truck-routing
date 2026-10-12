export type Level = 0 | 1 | 2 | 3 | 4;
export type Interval = 10 | 25 | 50;

export interface Place {
  lat: number;
  lng: number;
  label: string;
}

export interface AnalyzeRequest {
  origin: Place;
  destination: Place;
  departure_time: string; // ISO-8601 (UTC)
  load_weight_lb: number;
  interval_miles: Interval;
}

export interface Checkpoint {
  index: number;
  mile: number;
  lat: number;
  lng: number;
  eta: string;
  level: Level;
  label: string;
  drivers: string[];
  load_adjusted: boolean;
  wind_mph: number;
  rain_in_hr: number;
  snow_in_hr: number;
}

export interface RouteSummary {
  no_travel_miles: number;
  severe_miles: number;
  high_miles: number;
  moderate_miles: number;
  low_miles: number;
  avg_risk: number;
  max_level: Level;
  max_label: string;
}

export interface Route {
  id: string;
  distance_mi: number;
  duration_s: number;
  arrival: string;
  geometry: [number, number][]; // [lng, lat]
  summary: RouteSummary;
  checkpoints: Checkpoint[];
}

export interface HeatPoint {
  lat: number;
  lng: number;
  levels: Level[]; // one per forecast hour, 0..hours
}

export interface Analysis {
  departure_time: string;
  load_weight_lb: number;
  interval_miles: Interval;
  recommended_route_id: string;
  ranking: string[];
  reason: string;
  advisory: string | null;
  routes: Route[];
  heatmap: { hours: number; points: HeatPoint[] };
}

export type GeoResult = Place;
