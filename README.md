# Weather-Aware Truck Routing

React + Django app that compares three routes for a truck and recommends the safest one using weather
at the truck's **estimated arrival time** at each checkpoint, adjusted for **load weight**.

| Need | Provider (all free, no API key) |
|---|---|
| Routing (3 options) | OSRM |
| Weather (hourly, 16 days) | Open-Meteo |
| Place search | Photon (built for type-ahead) |
| Basemap tiles | OpenFreeMap (OSM's own tile servers prohibit app use) |

## Run locally

```bash
# API  (http://localhost:8000)
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
DEBUG=1 python manage.py runserver

# UI   (http://localhost:5173, proxies /api to :8000)
cd frontend && npm install && npm run dev

# Tests
cd backend && DEBUG=1 pytest
```

Deploy: `docker build -t truck-routing .` runs one container (Django serves the built UI and `/api`).
`render.yaml` is included for one-click Render deploys.

## How it works

```
POST /api/routes/analyze
  routing.py   OSRM -> up to 3 routes (via-point detours top up if OSRM returns fewer)
  analysis.py  checkpoints every 10/25/50 mi -> ETA per checkpoint -> ONE batched weather fetch
  risk.py      thresholds + load rules -> level per checkpoint
  scoring.py   miles by level -> rank -> human-readable reason
  heatmap      reuses the same weather series: risk level for every hour 0..48
```

`domain/` is pure Python (no Django, no IO) and holds all the business rules, so it is trivially unit-tested.
`services/` hold the integrations behind `Protocol`s (`RoutingProvider`, `WeatherProvider`); the only place
concrete classes are wired is `services/__init__.py`, and the API test swaps in fakes.

### Recommendation order (as specified)
1. Fewest **Severe** miles, 2. fewest **High** miles, 3. lowest average risk, 4. shortest time.
**No Travel** miles are compared before Severe, since a route with No Travel conditions is not drivable.
Miles per checkpoint = the stretch halfway to its neighbours. Comparisons are rounded (0.1 mi, 0.01 risk, 1 min)
so float noise never decides a winner. Average risk is compared to one decimal (0-4 scale), so a trivial risk
difference never beats a much faster route: that is the "balance risk and time" part of the brief. If every route hits No Travel, the UI says so and suggests delaying.

### Risk rules: interpretation
* Band edges shared by two bands (e.g. rain 0.25) resolve to the **higher** band; "No Travel" for rain/snow is strictly `>`.
* Load rules raise wind only: 45-54 mph and >30,000 lb is No Travel; 35-44 mph and >40,000 lb is Severe (never lowers a level).
* Rain/snow are in/hr (Open-Meteo hourly totals, `rain + showers`, and `snowfall`, in inches). Wind is 10 m sustained wind in mph.

### Performance
* One weather request set per analysis: all routes' checkpoints are de-duplicated onto a 0.05° grid, batched 50 per
  request, fetched in parallel and cached 30 min (Redis if `REDIS_URL` set). Heatmap data costs no extra calls.
* Route geometry is OSRM `overview=simplified`; the map uses MapLibre GL's GPU heatmap layer. Scrubbing the slider only
  updates one weight per point, so it stays smooth. Stale requests are aborted; geocoding is debounced.

### Assumptions and known limits
* OSRM has a car profile only. Durations are multiplied by `TRUCK_TIME_FACTOR` (1.15); truck restrictions (height, hazmat)
  are not modelled. Swap `OsrmRouting` for an HGV router (ORS, HERE) by implementing `RoutingProvider`.
* The public OSRM / Photon servers are rate-limited demo servers; self-host or add keys for production.
* ETA at a checkpoint is proportional to distance along the route, and weather uses the nearest forecast hour.
* Forecast range is 15 days, so departures are limited to the next 13 days (a 48 h heatmap window fits).
* Times are shown in the viewer's browser timezone.

## Loom outline (5-10 min)
1. Enter a trip, show the three routes and the recommendation reason (1 min).
2. Open `risk.py` / `scoring.py`: thresholds, load rules, ordering, tests (3 min).
3. Show a heavy load flipping the recommendation (same trip, 20,000 vs 42,000 lb) (1 min).
4. Heatmap slider 0-48 h, checkpoint table, popups (1 min).
5. Architecture: pure domain, provider protocols, batching and caching, trade-offs above (2 min).
