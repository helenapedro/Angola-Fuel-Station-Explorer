"""FastAPI application: REST API over the fuel-station dataset.

Run locally with::

    uvicorn api.main:app --reload

Interactive docs: http://127.0.0.1:8000/docs
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import db
from api.routers import stations
from api.schemas import Health

API_VERSION = "1.0.0"

app = FastAPI(
    title="Angola Fuel Station Explorer API",
    version=API_VERSION,
    description=(
        "JSON REST API over the Angolan fuel-station dataset. "
        "It reuses the same resilient data layer as the Dash dashboard "
        "(short-TTL cache, live upstream fetch, bundled fallback data)."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stations.router)


@app.get("/health", response_model=Health, tags=["meta"])
def health():
    df, source = db.load_stations_df()
    return Health(status="ok", version=API_VERSION, stations=len(df), source=source)


@app.get("/api/v1", tags=["meta"])
def api_index():
    return {
        "name": "Angola Fuel Station Explorer API",
        "version": API_VERSION,
        "endpoints": [
            "/health",
            "/api/v1/stations",
            "/api/v1/stations/{id}",
            "/api/v1/stations/stats",
            "/api/v1/stations/provinces",
            "/api/v1/stations/operators",
        ],
    }
