# Angola Fuel Station Explorer

A Dash application for exploring Angolan fuel stations through a single interactive dashboard. It consumes a public stations API, lets users filter stations by search, brand, province, municipality, and station name, and surfaces live errors when data is unavailable.

## Features

- Interactive station explorer with map-first layout.
- Filters for station search, brand, province, municipality, and station.
- Summary cards for total stations, brands, and municipalities in the current view.
- Clickable map markers with a selected-station detail panel.
- Graceful error states with short request timeouts and in-memory caching.

## Project Structure

- `app.py` - Dash app shell and navbar.
- `pages/map.py` - Main station explorer dashboard.
- `data_fetch.py` - Cached, timeout-bound data fetch helper for the API.
- `scrap.py` - Scraper for Pumangol station data into `gas_stations.json`.
- `mysqlConnect.py` - Loader to move scraped data into MySQL.
- `assets/styles.css` - Dashboard styling.

There is also a duplicated `src/` app tree in this repository. The root app is the current primary entrypoint.

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
- If the API fails, the UI shows an error and reuses cached data when available.

## Notes on Supporting Scripts

- `scrap.py` uses regex to extract station data from the Pumangol site; review the site structure before reusing it.
- `mysqlConnect.py` expects DB credentials via environment variables: `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`.
