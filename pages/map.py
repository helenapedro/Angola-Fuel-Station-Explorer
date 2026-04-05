import dash
from dash import Input, Output, callback

from data_fetch import get_stations_df
from map_dashboard.data import (
    apply_station_filters,
    build_filter_options,
    build_summary_counts,
    get_selected_station_name,
)
from map_dashboard.layout import build_dashboard_layout
from map_dashboard.presentation import build_empty_figure, build_map_figure, build_station_details

dash.register_page(__name__, path="/", name="Map", title="Home")

layout = build_dashboard_layout()


@callback(
    Output("operator-filter", "options"),
    Output("province-filter", "options"),
    Output("municipality-filter", "options"),
    Output("station-filter", "options"),
    Output("map-api-error", "children"),
    Input("map-refresh", "n_intervals"),
    Input("map-search", "value"),
    Input("operator-filter", "value"),
    Input("province-filter", "value"),
    Input("municipality-filter", "value"),
)
def refresh_filter_options(_, search_text, operator, province, municipality):
    df, err = get_stations_df()
    filtered_df = apply_station_filters(
        df,
        search_text=search_text,
        operator=operator,
        province=province,
        municipality=municipality,
    )

    filter_options = build_filter_options(df, filtered_df)
    return *filter_options, (err or "")


@callback(
    Output("gas-stations-map", "figure"),
    Output("station-count", "children"),
    Output("operator-count", "children"),
    Output("municipality-count", "children"),
    Output("selected-station-card", "children"),
    Input("map-refresh", "n_intervals"),
    Input("map-search", "value"),
    Input("operator-filter", "value"),
    Input("province-filter", "value"),
    Input("municipality-filter", "value"),
    Input("station-filter", "value"),
    Input("gas-stations-map", "clickData"),
)
def update_dashboard(_, search_text, operator, province, municipality, station, click_data):
    df, err = get_stations_df()
    filtered_df = apply_station_filters(
        df,
        search_text=search_text,
        operator=operator,
        province=province,
        municipality=municipality,
        station=station,
    )

    selected_station = get_selected_station_name(station, click_data)
    if filtered_df.empty:
        empty_message = err or "No stations available right now."
        return (
            build_empty_figure(empty_message),
            "0",
            "0",
            "0",
            build_station_details(filtered_df, None),
        )

    station_count, operator_count, municipality_count = build_summary_counts(filtered_df)
    return (
        build_map_figure(filtered_df, selected_station),
        station_count,
        operator_count,
        municipality_count,
        build_station_details(filtered_df, selected_station),
    )
