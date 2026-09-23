"""Single source of truth for station dataset normalization.

Both the Dash dashboard (``map_dashboard``) and the FastAPI API (``api``)
consume this module, so the cleaning rules, canonical column names, the
coordinate-validity definition, and stable station IDs live in exactly one
place. Consumers apply only view-level filters on top of the frame
returned here.
"""

import hashlib
import math

import pandas as pd

# Canonical field -> column-name aliases, in priority order. The bundled
# fallback dataset uses the capitalized names; the live API may differ.
COLUMN_ALIASES = {
    "operator": ["operator", "Operator"],
    "station": ["station", "Station", "name"],
    "address": ["address", "Address"],
    "municipality": ["municipality", "Municipality"],
    "province": ["province", "Province", "state"],
    "country": ["country", "Country"],
    "latitude": ["latitude", "Latitude", "lat"],
    "longitude": ["longitude", "Longitude", "lon", "lng"],
}

CANONICAL_COLUMNS = list(COLUMN_ALIASES)
TEXT_COLUMNS = ("operator", "station", "address", "municipality", "province", "country")
FLOAT_COLUMNS = ("latitude", "longitude")

ANGOLA_LATITUDE_RANGE = (-18.1, -4.3)
ANGOLA_LONGITUDE_RANGE = (11.4, 24.2)


def _resolve_column(df: pd.DataFrame, aliases: list) -> str | None:
    for alias in aliases:
        if alias in df.columns:
            return alias
    return None


def _clean_text(value) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) and pd.isna(value):
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


def stable_station_id(operator, station, latitude, longitude) -> int:
    """Return a deterministic ID for a station.

    The ID is derived from the operator, station name, and coordinates, so
    it stays the same across dataset refreshes as long as those fields
    don't change — unlike a positional row number, which shifts whenever
    the snapshot is rebuilt. 48 bits keeps collision odds negligible at
    this dataset's scale.
    """
    key = "|".join(
        [
            (operator or "").strip().lower(),
            (station or "").strip().lower(),
            f"{latitude:.6f}" if latitude is not None else "",
            f"{longitude:.6f}" if longitude is not None else "",
        ]
    )
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return int(digest[:12], 16)


def normalize_stations_df(df: pd.DataFrame) -> pd.DataFrame:
    """Return the canonical stations frame.

    Columns are the lowercase canonical names plus a leading stable ``id``.
    Text is stripped (empty becomes None), coordinates are coerced to
    float (invalid becomes None). No rows are dropped here — deciding
    which rows are usable is a view-level concern (see
    :func:`valid_coordinates_mask`).
    """
    normalized = pd.DataFrame()
    for canonical, aliases in COLUMN_ALIASES.items():
        column = _resolve_column(df, aliases)
        normalized[canonical] = df[column] if column is not None else None

    for column in TEXT_COLUMNS:
        # Build an explicit object-dtype column so missing values stay None.
        # (On pandas 3.x, .map() over the default str dtype turns None into
        # NaN, which would then leak into API responses as invalid values.)
        cleaned = [_clean_text(value) for value in normalized[column].tolist()]
        normalized[column] = pd.Series(cleaned, dtype=object, index=normalized.index)
    for column in FLOAT_COLUMNS:
        normalized[column] = normalized[column].map(_clean_float)

    normalized["id"] = [
        stable_station_id(row.operator, row.station, row.latitude, row.longitude)
        for row in normalized.itertuples()
    ]
    return normalized[["id", *CANONICAL_COLUMNS]]


def valid_coordinates_mask(df: pd.DataFrame) -> pd.Series:
    """True for rows with usable map coordinates.

    Drops rows without coordinates, the (0, 0) "null island" placeholder,
    and coordinates outside Angola's bounding box.
    """
    has_coordinates = df["latitude"].notna() & df["longitude"].notna()
    is_not_null_island = (df["latitude"] != 0) & (df["longitude"] != 0)
    is_in_angola = df["latitude"].between(*ANGOLA_LATITUDE_RANGE) & df["longitude"].between(
        *ANGOLA_LONGITUDE_RANGE
    )
    return has_coordinates & is_not_null_island & is_in_angola
