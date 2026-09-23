"""FastAPI application: REST API over the fuel-station dataset.

Run locally with::

    uvicorn api.main:app --reload

Interactive docs: http://127.0.0.1:8000/docs
"""

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute

from api.deps import StationData, get_station_data
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
def health(station_data: StationData = Depends(get_station_data)):
    df, source = station_data
    return Health(status="ok", version=API_VERSION, stations=len(df), source=source)


@app.get("/api/v1", tags=["meta"])
def api_index():
    # Derived from the registered routes so it can't go stale when
    # endpoints are added or renamed. (In recent FastAPI versions
    # include_router nests routes instead of flattening them into
    # app.routes, hence the explicit router list.)
    sources = [app, stations.router]
    endpoints = sorted(
        f"{' '.join(sorted(route.methods))} {route.path}"
        for source in sources
        for route in source.routes
        if isinstance(route, APIRoute)
    )
    return {
        "name": "Angola Fuel Station Explorer API",
        "version": API_VERSION,
        "endpoints": endpoints,
    }
