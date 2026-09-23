"""Resilient local data loading for the station dataset.

The primary source is the bundled ``data/stations_clean.json`` snapshot,
rebuilt weekly by the ingestion workflow. A short-TTL in-memory cache
avoids re-parsing the file on every request. If the snapshot is missing or
unreadable, the original ``gas_stations.json`` bundle is used as a
last-resort fallback (flagged via :func:`is_fallback_data`).
"""

import json
import time
from pathlib import Path
from typing import Tuple

import pandas as pd

CACHE_TTL_SECONDS = 300
CLEAN_DATA_PATH = Path(__file__).parent / "data" / "stations_clean.json"
LEGACY_FALLBACK_DATA_PATH = Path(__file__).with_name("gas_stations.json")
FALLBACK_OPERATOR = "Pumangol"

_CACHE = {"df": None, "fetched_at": 0.0, "error": None, "is_fallback": False}


def _split_city(city: str) -> Tuple[str, str]:
    parts = [part.strip() for part in str(city or "").split("-") if part.strip()]
    if len(parts) >= 2:
        return parts[-1], parts[0]
    if parts:
        return parts[0], parts[0]
    return "", ""


def _read_station_list(path: Path) -> list:
    with path.open("r", encoding="utf-8") as data_file:
        payload = json.load(data_file)

    stations = payload.get("stations", payload) if isinstance(payload, dict) else payload
    if not isinstance(stations, list):
        raise ValueError(f"{path} must contain a station list or a stations object")
    return stations


def _stations_to_df(stations: list) -> pd.DataFrame:
    rows = []
    for station in stations:
        municipality, parsed_province = _split_city(station.get("city"))
        rows.append(
            {
                "Operator": station.get("operator") or station.get("Operator") or FALLBACK_OPERATOR,
                "Station": station.get("station") or station.get("name") or station.get("Station"),
                "Address": station.get("address"),
                "Latitude": station.get("latitude"),
                "Longitude": station.get("longitude"),
                "Municipality": station.get("municipality") or municipality,
                "Province": station.get("province") or station.get("state") or parsed_province,
                "Country": station.get("country") or "Angola",
            }
        )
    return pd.DataFrame(rows)


def _load_clean_df() -> pd.DataFrame:
    """Load the weekly-refreshed bundled snapshot (primary source)."""
    return _stations_to_df(_read_station_list(CLEAN_DATA_PATH))


def _load_fallback_df() -> pd.DataFrame:
    """Load the legacy bundled snapshot (last-resort fallback)."""
    return _stations_to_df(_read_station_list(LEGACY_FALLBACK_DATA_PATH))


def _cache_df(df: pd.DataFrame, now: float, error: str = None, is_fallback: bool = False) -> None:
    _CACHE.update({"df": df, "fetched_at": now, "error": error, "is_fallback": is_fallback})


def get_stations_df() -> Tuple[pd.DataFrame, str]:
    """Load station data with a short TTL cache and safe fallbacks."""
    now = time.time()
    cached_df = _CACHE["df"]
    cached_error = _CACHE["error"]

    if cached_df is not None and now - _CACHE["fetched_at"] < CACHE_TTL_SECONDS:
        # Return a copy so downstream mutations don't affect cache.
        return cached_df.copy(), cached_error

    try:
        df = _load_clean_df()
    except (OSError, ValueError, TypeError) as exc:
        # Primary snapshot missing or unreadable: prefer stale-but-usable
        # cached data, then the legacy bundled fallback, over an error page.
        if cached_df is not None:
            return cached_df.copy(), f"Showing cached station data because the bundled snapshot is unavailable: {exc}"

        try:
            fallback_df = _load_fallback_df()
        except (OSError, ValueError, TypeError) as fallback_exc:
            return pd.DataFrame(), f"Unable to load station data: {exc}; fallback data unavailable: {fallback_exc}"

        warning = f"Showing bundled fallback station data because the primary snapshot is unavailable: {exc}"
        _cache_df(fallback_df, now, error=warning, is_fallback=True)
        return fallback_df.copy(), warning

    _cache_df(df, now)
    return df.copy(), None


def is_fallback_data() -> bool:
    """Return True when the cached station data came from the bundled fallback."""
    return bool(_CACHE["is_fallback"])
