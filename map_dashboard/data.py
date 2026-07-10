"""Data preparation helpers for the station explorer dashboard."""

import pandas as pd

SEARCHABLE_COLUMNS = ["Operator", "Station", "Address", "Municipality", "Province", "Country"]
EXPECTED_COLUMNS = SEARCHABLE_COLUMNS + ["Latitude", "Longitude"]
ANGOLA_LATITUDE_RANGE = (-18.1, -4.3)
ANGOLA_LONGITUDE_RANGE = (11.4, 24.2)


def normalize_stations_df(df):
    if df.empty:
        return df

    clean_df = df.copy()
    for column in EXPECTED_COLUMNS:
        if column not in clean_df.columns:
            clean_df[column] = None

    for column in SEARCHABLE_COLUMNS:
        clean_df[column] = clean_df[column].fillna("").astype(str).str.strip()

    clean_df["search_blob"] = (
        clean_df["Station"] + " " + clean_df["Address"] + " " + clean_df["Municipality"] + " " + clean_df["Province"]
    ).str.lower()

    clean_df["Latitude"] = pd.to_numeric(clean_df["Latitude"], errors="coerce")
    clean_df["Longitude"] = pd.to_numeric(clean_df["Longitude"], errors="coerce")

    has_coordinates = clean_df["Latitude"].notna() & clean_df["Longitude"].notna()
    is_not_null_island = (clean_df["Latitude"] != 0) & (clean_df["Longitude"] != 0)
    is_in_angola = clean_df["Latitude"].between(*ANGOLA_LATITUDE_RANGE) & clean_df["Longitude"].between(
        *ANGOLA_LONGITUDE_RANGE
    )
    return clean_df[has_coordinates & is_not_null_island & is_in_angola]


def apply_station_filters(df, search_text=None, operator=None, province=None, municipality=None, station=None):
    filtered_df = normalize_stations_df(df)
    if filtered_df.empty:
        return filtered_df

    if search_text:
        query = search_text.strip().lower()
        filtered_df = filtered_df[filtered_df["search_blob"].str.contains(query, regex=False, na=False)]
    if operator:
        filtered_df = filtered_df[filtered_df["Operator"] == operator]
    if province:
        filtered_df = filtered_df[filtered_df["Province"] == province]
    if municipality:
        filtered_df = filtered_df[filtered_df["Municipality"] == municipality]
    if station:
        filtered_df = filtered_df[filtered_df["Station"] == station]

    return filtered_df


def build_dropdown_options(values):
    return [{"label": value, "value": value} for value in values if value]


def build_filter_options(df, filtered_df):
    normalized_df = normalize_stations_df(df)
    operator_options = build_dropdown_options(sorted(normalized_df["Operator"].dropna().unique())) if not normalized_df.empty else []
    province_options = build_dropdown_options(sorted(filtered_df["Province"].dropna().unique())) if not filtered_df.empty else []
    municipality_options = build_dropdown_options(sorted(filtered_df["Municipality"].dropna().unique())) if not filtered_df.empty else []
    station_options = build_dropdown_options(sorted(filtered_df["Station"].dropna().unique())) if not filtered_df.empty else []
    return operator_options, province_options, municipality_options, station_options


def get_selected_station_name(selected_station, click_data):
    if click_data and click_data.get("points"):
        point_data = click_data["points"][0].get("customdata") or []
        if point_data:
            return point_data[0]
    return selected_station


def build_summary_counts(filtered_df):
    if filtered_df.empty:
        return "0", "0", "0"

    station_count = f"{len(filtered_df):,}"
    operator_count = f'{filtered_df["Operator"].replace("", None).dropna().nunique():,}'
    municipality_count = f'{filtered_df["Municipality"].replace("", None).dropna().nunique():,}'
    return station_count, operator_count, municipality_count
