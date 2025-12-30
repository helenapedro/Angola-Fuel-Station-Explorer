import time
from typing import Tuple

import pandas as pd
import requests

API_URL = "https://gaspump-18b4eae89030.herokuapp.com/api/stations"
CACHE_TTL_SECONDS = 60
REQUEST_TIMEOUT_SECONDS = 5

_CACHE = {"df": None, "fetched_at": 0.0, "error": None}


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
        data = response.json()
        df = pd.DataFrame(data)
        _CACHE.update({"df": df, "fetched_at": now, "error": None})
        return df.copy(), None
    except requests.RequestException as exc:
        error_message = f"Unable to fetch station data: {exc}"
        # If we have cached data, keep using it but surface the error.
        if cached_df is not None:
            _CACHE["error"] = error_message
            return cached_df.copy(), error_message
        return pd.DataFrame(), error_message
