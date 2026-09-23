"""Data access for the REST API.

The API reuses the project's resilient data layer
(:func:`data_fetch.get_stations_df`): short-TTL in-memory cache, a live
upstream fetch with a 5s timeout, and bundled fallback data when the
upstream source is unavailable. This module only normalizes whatever
that layer returns into a canonical, JSON-safe shape.
"""

import math

import pandas as pd

import data_fetch

# Canonical field -> column-name aliases, in priority order. The bundled
# fallback dataset uses the capitalized names; the live API may differ.
_COLUMN_ALIASES = {
    "operator": ["operator", "Operator"],
    "station": ["station", "Station", "name"],
    "address": ["address", "Address"],
    "municipality": ["municipality", "Municipality"],
    "province": ["province", "Province", "state"],
    "country": ["country", "Country"],
    "latitude": ["latitude", "Latitude", "lat"],
    "longitude": ["longitude", "Longitude", "lon", "lng"],
}

_CANONICAL_COLUMNS = list(_COLUMN_ALIASES)


def _resolve_column(df: pd.DataFrame, aliases: list) -> str | None:
    for alias in aliases:
        if alias in df.columns:
            return alias
    return None


def _clean_text(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    text = str(value).strip()
    return text or None


def _clean_float(value) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number):
        return None
    return number


def load_stations_df() -> tuple:
    """Return ``(normalized stations DataFrame, source label)``.

    The frame always carries the canonical columns plus a 1-based
    positional ``id``. IDs are stable only within one dataset snapshot —
    they identify rows, not real-world entities.
    """
    raw_df, warning = data_fetch.get_stations_df()

    normalized = pd.DataFrame()
    for canonical, aliases in _COLUMN_ALIASES.items():
        column = _resolve_column(raw_df, aliases)
        normalized[canonical] = raw_df[column] if column is not None else None

    for column in ("operator", "station", "address", "municipality", "province", "country"):
        normalized[column] = normalized[column].map(_clean_text)
    for column in ("latitude", "longitude"):
        normalized[column] = normalized[column].map(_clean_float)

    normalized = normalized.reset_index(drop=True)
    normalized.insert(0, "id", normalized.index + 1)

    source = "fallback" if warning and "fallback" in warning.lower() else "live"
    return normalized, source
