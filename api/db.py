"""Data access for the REST API.

The API reuses the project's resilient data layer
(:func:`data_fetch.get_stations_df`): short-TTL in-memory cache over the
weekly-refreshed bundled snapshot, with legacy bundled fallback data when
the snapshot is unavailable. Normalization (cleaning rules, canonical
columns, stable IDs) lives in :mod:`station_data`, shared with the
dashboard.
"""

import pandas as pd

import data_fetch
import station_data


def load_stations_df() -> tuple[pd.DataFrame, str]:
    """Return ``(normalized stations DataFrame, source label)``.

    The frame carries the canonical columns plus a stable ``id`` that is
    deterministic across dataset refreshes (derived from operator, name,
    and coordinates), so ``/stations/{id}`` links don't shift when the
    underlying snapshot is rebuilt. The source label is ``"fallback"``
    when the data came from the bundled fallback dataset, otherwise
    ``"live"``.
    """
    raw_df, _warning = data_fetch.get_stations_df()

    normalized = station_data.normalize_stations_df(raw_df)

    source = "fallback" if data_fetch.is_fallback_data() else "live"
    return normalized, source
