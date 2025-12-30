# Angola Fuel Station Explorer

A Dash application that visualizes Angolan gas stations on an interactive map, a filterable table, and simple statistics. It consumes a public stations API, supports CSV export, and surfaces live errors when data is unavailable.

## Features

- Map view with address highlighting and periodic refresh (cached to reduce API load).
- Table view with municipality filter, CSV export, and clipboard copy of selected rows.
- Stats view with totals plus operator and municipality distributions.
- Graceful error states: short request timeouts, in-app alerts, and a 60s data cache fallback.

## Project Structure

- `src/app.py` – Dash app shell, navbar, and page registration.
- `src/pages/map.py` – Mapbox scatter map with optional address focus.
- `src/pages/table.py` – Filterable/exportable data table with copy support.
- `src/pages/stats.py` – Summary metrics and distribution charts.
- `src/data_fetch.py` – Cached, timeout-bound data fetch helper for the API.
- `src/scrap.py` – Scraper for Pumangol station data into `gas_stations.json`.
- `src/mysqlConnect.py` – Loader to move scraped data into MySQL (requires credentials).

## Getting Started

1. Create and activate a Python 3.10+ virtual environment.
2. `pip install -r src/requirements.txt`
3. Run the app locally:
   ```bash
   cd src
   python app.py
   ```
   The app starts on `http://127.0.0.1:8050/`.

## Deployment

- Procfile for Gunicorn: `web: gunicorn app:server` (run from `src/`).
- Ensure environment variables are set in your host (never commit secrets).

## Data Source & Resilience

- Stations are fetched from `https://gaspump-18b4eae89030.herokuapp.com/api/stations`.
- Each fetch uses a 5s timeout and 60s in-memory cache. If the API fails, the UI shows a warning and reuses cached data when available.

## Notes on Supporting Scripts

- `src/scrap.py` uses regex to extract station data from the Pumangol site; review the site structure before reusing.
- `src/mysqlConnect.py` expects DB credentials via environment variables: `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`. Rotate any leaked secrets and avoid storing them in `.env` files committed to the repo
