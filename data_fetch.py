import json
import os
import time
from pathlib import Path
from typing import Tuple

import pandas as pd
import requests

API_URL = os.getenv("STATIONS_API_URL", "https://gaspump-18b4eae89030.herokuapp.com/api/stations")
CACHE_TTL_SECONDS = 300
REQUEST_TIMEOUT_SECONDS = 5
FALLBACK_DATA_PATH = Path(__file__).with_name("gas_stations.json")
FALLBACK_OPERATOR = "Pumangol"

_CACHE = {"df": None, "fetched_at": 0.0, "error": None, "is_fallback": False}


def _split_city(city: str) -> Tuple[str, str]:
    parts = [part.strip() for part in str(city or "").split("-") if part.strip()]
    if len(parts) >= 2:
        return parts[-1], parts[0]
    if parts:
        return parts[0], parts[0]
    return "", ""


def _load_fallback_df() -> pd.DataFrame:
    with FALLBACK_DATA_PATH.open("r", encoding="utf-8") as fallback_file:
        stations = json.load(fallback_file)

    rows = []
    for station in stations:
        municipality, parsed_province = _split_city(station.get("city"))
        rows.append(
            {
                "Operator": FALLBACK_OPERATOR,
                "Station": station.get("name"),
                "Address": station.get("address"),
                "Latitude": station.get("latitude"),
                "Longitude": station.get("longitude"),
                "Municipality": municipality,
                "Province": station.get("state") or parsed_province,
                "Country": station.get("country") or "Angola",
            }
        )
    return pd.DataFrame(rows)


def _cache_df(df: pd.DataFrame, now: float, error: str = None, is_fallback: bool = False) -> None:
    _CACHE.update({"df": df, "fetched_at": now, "error": error, "is_fallback": is_fallback})


def get_stations_df() -> Tuple[pd.DataFrame, str]:
    """Fetch station data with a short TTL cache and safe fallbacks."""
    now = time.time()
    cached_df = _CACHE["df"]
    cached_error = _CACHE["error"]

    if cached_df is not None and now - _CACHE["fetched_at"] < CACHE_TTL_SECONDS:
        # Return a copy so downstream mutations don't affect cache.
        return cached_df.copy(), cached_error

    try:
        response = requests.get(API_URL, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        try:
            data = response.json()
        except ValueError as exc:
            raise requests.RequestException(f"Invalid JSON response: {exc}") from exc
        df = pd.DataFrame(data)
        _cache_df(df, now)
        return df.copy(), None
    except requests.RequestException as exc:
        # If we have usable data, prefer a working dashboard over surfacing an
        # intermittent upstream timeout to users.
        if cached_df is not None:
            return cached_df.copy(), None

        try:
            fallback_df = _load_fallback_df()
        except (OSError, ValueError, TypeError) as fallback_exc:
            return pd.DataFrame(), f"Unable to fetch station data: {exc}; fallback data unavailable: {fallback_exc}"

        _cache_df(fallback_df, now, is_fallback=True)
        return fallback_df.copy(), None
