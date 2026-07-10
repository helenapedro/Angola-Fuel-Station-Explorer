# Angola Fuel Station Explorer

A Dash application for exploring Angolan fuel stations through a single interactive dashboard. It consumes a public stations API, lets users filter stations by search, brand, province, municipality, and station name, and surfaces live errors when data is unavailable.

## Features

- Interactive station explorer with map-first layout.
- Filters for station search, brand, province, municipality, and station.
- Summary cards for total stations, brands, and municipalities in the current view.
- Clickable map markers with a selected-station detail panel.
- Graceful data loading with short request timeouts, in-memory caching, and bundled fallback station data.

## Project Structure

- `app.py` - Dash app shell and navbar.
- `pages/map.py` - Main station explorer dashboard.
- `data_fetch.py` - Cached, timeout-bound data fetch helper for the API with local fallback data.
- `ingestion/` - Multi-source station ingestion, normalization, validation, and clean/rejected output generation.
- `scrap.py` - Compatibility wrapper for `python -m ingestion.sync_stations`.
- `mysqlConnect.py` - Loader to move scraped data into MySQL.
- `docs/data-ingestion.md` - Data-source strategy and refresh runbook.
- `assets/styles.css` - Dashboard styling.

## Getting Started

1. Create and activate a Python 3.10+ virtual environment.
2. Install dependencies:
   ```powershell
   python -m pip install -r requirements.txt
   ```
3. Run the app locally:
   ```powershell
   python app.py
   ```
4. Open `http://127.0.0.1:8050/`.

## Deployment

- Procfile for Gunicorn: `web: gunicorn app:server`
- Ensure environment variables are set in your host and do not commit secrets.

## Data Source & Resilience

- Stations are fetched from `https://gaspump-18b4eae89030.herokuapp.com/api/stations`.
- Each fetch uses a 5 second timeout and a 5 minute in-memory cache.
- If the API fails, the dashboard reuses cached data when available and shows a stale-data warning. If no cache exists yet, it loads bundled station data from `data/stations_clean.json` when present, then falls back to `gas_stations.json`.
- Set `STATIONS_API_URL` to point the dashboard at a different stations API.

## Refreshing Station Data

No documented official/public Angola fuel-station API has been identified for government, Sonangol, Pumangol, Galp/Sonangalp, or regulator-style sources. The project therefore uses a multi-source ingestion plan:

- OpenStreetMap Overpass API as the public baseline source for `amenity=fuel` stations in Angola.
- Operator website adapters for brand/operator-owned station listings.
- Validation, source health tracking, stale-source reuse, deduplication, and rejected-record output before data reaches the dashboard.

Build only from the bundled legacy JSON:

```powershell
python -m ingestion.sync_stations --offline
```

Build from live sources where network access is available:

```powershell
python -m ingestion.sync_stations
```

See `docs/data-ingestion.md` for the full source strategy, output schema, and runbook.

## Notes on Supporting Scripts

- `scrap.py` is retained only for compatibility and delegates to the ingestion pipeline.
- `mysqlConnect.py` expects DB credentials via environment variables: `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`.
