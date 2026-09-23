"""Shared FastAPI dependencies for the REST API."""

import pandas as pd

from api import db

# The normalized stations frame plus the source label ("live"/"fallback").
StationData = tuple[pd.DataFrame, str]


def get_station_data() -> StationData:
    """Provide the stations dataset to endpoints.

    A single dependency keeps the ``db.load_stations_df()`` call in one
    place instead of repeating it in every handler, and lets tests swap
    the dataset with ``app.dependency_overrides`` instead of patching.
    """
    return db.load_stations_df()
