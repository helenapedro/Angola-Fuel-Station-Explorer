"""Data preparation helpers for the station explorer dashboard."""

import pandas as pd

import station_data

SEARCHABLE_COLUMNS = ["operator", "station", "address", "municipality", "province", "country"]


def normalize_stations_df(df):
    """Dashboard view of the dataset: canonical frame, map-ready rows only.

    Cleaning rules come from :mod:`station_data` (shared with the API);
    this wrapper only drops rows without usable map coordinates and adds
    the free-text search blob.
    """
    normalized = station_data.normalize_stations_df(df)
    if normalized.empty:
        return normalized

    clean_df = normalized[station_data.valid_coordinates_mask(normalized)].copy()

    for column in SEARCHABLE_COLUMNS:
        clean_df[column] = clean_df[column].fillna("").astype(str).str.strip()

    clean_df["search_blob"] = (
        clean_df["station"] + " " + clean_df["address"] + " " + clean_df["municipality"] + " " + clean_df["province"]
    ).str.lower()

    return clean_df


def apply_station_filters(df, search_text=None, operator=None, province=None, municipality=None, station=None):
    filtered_df = normalize_stations_df(df)
    if filtered_df.empty:
        return filtered_df

    if search_text:
        query = search_text.strip().lower()
        filtered_df = filtered_df[filtered_df["search_blob"].str.contains(query, regex=False, na=False)]
    if operator:
        filtered_df = filtered_df[filtered_df["operator"] == operator]
    if province:
        filtered_df = filtered_df[filtered_df["province"] == province]
    if municipality:
        filtered_df = filtered_df[filtered_df["municipality"] == municipality]
    if station:
        filtered_df = filtered_df[filtered_df["station"] == station]

    return filtered_df


def build_dropdown_options(values, show_counts=True):
    """Dropdown options labeled with result counts, e.g. ``Luanda (45)``.

    Counts make the cascading filters scannable; the station dropdown
    passes ``show_counts=False`` since every station is unique.
    """
    series = values.dropna().astype(str).str.strip()
    series = series[series != ""]
    if show_counts:
        counts = series.value_counts()
        return [
            {"label": f"{value} ({count:,})", "value": value}
            for value, count in sorted(counts.items())
        ]
    return [{"label": value, "value": value} for value in sorted(series.unique())]


def build_filter_options(df, filtered_df):
    normalized_df = normalize_stations_df(df)
    operator_options = build_dropdown_options(normalized_df["operator"]) if not normalized_df.empty else []
    province_options = build_dropdown_options(filtered_df["province"]) if not filtered_df.empty else []
    municipality_options = build_dropdown_options(filtered_df["municipality"]) if not filtered_df.empty else []
    station_options = build_dropdown_options(filtered_df["station"], show_counts=False) if not filtered_df.empty else []
    return operator_options, province_options, municipality_options, station_options


def get_selected_station_name(selected_station, click_data):
    if click_data and click_data.get("points"):
        point_data = click_data["points"][0].get("customdata") or []
        if point_data:
            return point_data[0]
    return selected_station


def build_summary_counts(filtered_df):
    if filtered_df.empty:
        return "0", "0", "0", "0"

    station_count = f"{len(filtered_df):,}"
    operator_count = f'{filtered_df["operator"].replace("", None).dropna().nunique():,}'
    province_count = f'{filtered_df["province"].replace("", None).dropna().nunique():,}'
    municipality_count = f'{filtered_df["municipality"].replace("", None).dropna().nunique():,}'
    return station_count, operator_count, province_count, municipality_count
