import dash
import dash_bootstrap_components as dbc
import plotly.express as px
from dash import Input, Output, callback, dcc, html

from data_fetch import get_stations_df

dash.register_page(__name__, path="/", name="Map", title="Home")

MAP_HEIGHT = 680
EMPTY_FIGURE_CENTER = {"lat": -11.2027, "lon": 17.8739}


def _safe_text(value, fallback="Not available"):
    if value is None:
        return fallback
    text = str(value).strip()
    return text if text else fallback


def _normalize_df(df):
    if df.empty:
        return df

    clean_df = df.copy()
    expected_columns = ["Operator", "Station", "Address", "Municipality", "Province", "Country", "Latitude", "Longitude"]
    for column in expected_columns:
        if column not in clean_df.columns:
            clean_df[column] = None

    for column in ["Operator", "Station", "Address", "Municipality", "Province", "Country"]:
        clean_df[column] = clean_df[column].fillna("").astype(str).str.strip()

    clean_df["search_blob"] = (
        clean_df["Station"] + " " + clean_df["Address"] + " " + clean_df["Municipality"] + " " + clean_df["Province"]
    ).str.lower()

    clean_df["Latitude"] = clean_df["Latitude"].fillna(0)
    clean_df["Longitude"] = clean_df["Longitude"].fillna(0)
    clean_df = clean_df[(clean_df["Latitude"] != 0) & (clean_df["Longitude"] != 0)]
    return clean_df


def _apply_filters(df, search_text=None, operator=None, province=None, municipality=None, station=None):
    filtered_df = _normalize_df(df)
    if filtered_df.empty:
        return filtered_df

    if search_text:
        filtered_df = filtered_df[filtered_df["search_blob"].str.contains(search_text.strip().lower(), na=False)]
    if operator:
        filtered_df = filtered_df[filtered_df["Operator"] == operator]
    if province:
        filtered_df = filtered_df[filtered_df["Province"] == province]
    if municipality:
        filtered_df = filtered_df[filtered_df["Municipality"] == municipality]
    if station:
        filtered_df = filtered_df[filtered_df["Station"] == station]

    return filtered_df


def _dropdown_options(values):
    return [{"label": value, "value": value} for value in values if value]


def _build_empty_figure(message):
    fig = px.scatter_mapbox(lat=[], lon=[], zoom=4, height=MAP_HEIGHT)
    fig.update_layout(
        mapbox_style="open-street-map",
        mapbox_center=EMPTY_FIGURE_CENTER,
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        paper_bgcolor="#f6efe7",
        annotations=[
            {
                "text": message,
                "xref": "paper",
                "yref": "paper",
                "x": 0.5,
                "y": 0.5,
                "showarrow": False,
                "font": {"size": 16, "color": "#6f3b2b"},
            }
        ],
    )
    return fig


def _build_map_figure(filtered_df, selected_station):
    if filtered_df.empty:
        return _build_empty_figure("No stations match the current filters.")

    center = {
        "lat": filtered_df["Latitude"].mean(),
        "lon": filtered_df["Longitude"].mean(),
    }
    zoom = 5 if len(filtered_df) > 1 else 11

    fig = px.scatter_mapbox(
        filtered_df,
        lat="Latitude",
        lon="Longitude",
        color="Operator",
        hover_name="Station",
        hover_data={
            "Operator": True,
            "Municipality": True,
            "Province": True,
            "Address": True,
            "Latitude": False,
            "Longitude": False,
        },
        custom_data=["Station", "Operator", "Municipality", "Province", "Address", "Country"],
        zoom=zoom,
        height=MAP_HEIGHT,
    )

    fig.update_traces(marker={"size": 12, "opacity": 0.9})
    fig.update_layout(
        mapbox_style="open-street-map",
        mapbox_center=center,
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        paper_bgcolor="#f6efe7",
        plot_bgcolor="#f6efe7",
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.01,
            "xanchor": "left",
            "x": 0,
            "title": {"text": ""},
        },
    )

    if selected_station:
        selected_row = filtered_df[filtered_df["Station"] == selected_station]
        if not selected_row.empty:
            fig.add_scattermapbox(
                lat=selected_row["Latitude"],
                lon=selected_row["Longitude"],
                mode="markers",
                marker={"size": 20, "color": "#f4a261", "opacity": 1},
                hoverinfo="skip",
                showlegend=False,
            )

    return fig


def _build_station_details(filtered_df, selected_station):
    if filtered_df.empty:
        return html.Div(
            "No station available for the current filters.",
            className="map-dashboard__detail-empty",
        )

    station_row = filtered_df.iloc[0]
    if selected_station:
        selected_rows = filtered_df[filtered_df["Station"] == selected_station]
        if not selected_rows.empty:
            station_row = selected_rows.iloc[0]

    items = [
        ("Brand", station_row.get("Operator")),
        ("Station", station_row.get("Station")),
        ("Address", station_row.get("Address")),
        ("Municipality", station_row.get("Municipality")),
        ("Province", station_row.get("Province")),
        ("Country", station_row.get("Country")),
        ("Coordinates", f'{station_row.get("Latitude")}, {station_row.get("Longitude")}'),
    ]

    return html.Div(
        [
            html.Div("Selected Station", className="map-dashboard__panel-title"),
            html.H4(_safe_text(station_row.get("Station")), className="map-dashboard__detail-name"),
            html.Div(_safe_text(station_row.get("Operator")), className="map-dashboard__detail-brand"),
            html.Div(
                [
                    html.Div(
                        [
                            html.Span(label, className="map-dashboard__detail-label"),
                            html.Span(_safe_text(value), className="map-dashboard__detail-value"),
                        ],
                        className="map-dashboard__detail-row",
                    )
                    for label, value in items
                ]
            ),
        ]
    )


layout = html.Div(
    [
        html.Div(
            [
                html.Div("Station Finder", className="map-dashboard__eyebrow"),
                html.H1("Explore fuel stations with the details you already have.", className="map-dashboard__title"),
                html.P(
                    "Filter by operator, province, municipality, or station name and inspect location details directly from the map.",
                    className="map-dashboard__subtitle",
                ),
            ],
            className="map-dashboard__hero",
        ),
        html.Div(id="map-api-error", className="map-dashboard__error"),
        html.Div(
            [
                html.Div(
                    [
                        dbc.Card(
                            dbc.CardBody(
                                [
                                    html.Div("Filters", className="map-dashboard__panel-title"),
                                    dbc.Label("Search"),
                                    dcc.Input(
                                        id="map-search",
                                        type="text",
                                        placeholder="Search station, address, municipality...",
                                        className="map-dashboard__input",
                                    ),
                                    dbc.Label("Brand", className="map-dashboard__label"),
                                    dcc.Dropdown(id="operator-filter", options=[], placeholder="All brands"),
                                    dbc.Label("Province", className="map-dashboard__label"),
                                    dcc.Dropdown(id="province-filter", options=[], placeholder="All provinces"),
                                    dbc.Label("Municipality", className="map-dashboard__label"),
                                    dcc.Dropdown(id="municipality-filter", options=[], placeholder="All municipalities"),
                                    dbc.Label("Station", className="map-dashboard__label"),
                                    dcc.Dropdown(id="station-filter", options=[], placeholder="All stations"),
                                ]
                            ),
                            className="map-dashboard__panel",
                        ),
                        dbc.Card(
                            dbc.CardBody(html.Div(id="selected-station-card")),
                            className="map-dashboard__panel map-dashboard__detail-panel",
                        ),
                    ],
                    className="map-dashboard__sidebar",
                ),
                html.Div(
                    [
                        html.Div(
                            [
                                dbc.Card(
                                    dbc.CardBody([html.Div("Stations", className="map-dashboard__stat-label"), html.Div(id="station-count", className="map-dashboard__stat-value")]),
                                    className="map-dashboard__stat-card",
                                ),
                                dbc.Card(
                                    dbc.CardBody([html.Div("Brands", className="map-dashboard__stat-label"), html.Div(id="operator-count", className="map-dashboard__stat-value")]),
                                    className="map-dashboard__stat-card",
                                ),
                                dbc.Card(
                                    dbc.CardBody([html.Div("Municipalities", className="map-dashboard__stat-label"), html.Div(id="municipality-count", className="map-dashboard__stat-value")]),
                                    className="map-dashboard__stat-card",
                                ),
                            ],
                            className="map-dashboard__stats",
                        ),
                        dbc.Card(
                            dbc.CardBody(
                                dcc.Graph(
                                    id="gas-stations-map",
                                    config={"displayModeBar": False},
                                    className="map-dashboard__map",
                                )
                            ),
                            className="map-dashboard__map-card",
                        ),
                    ],
                    className="map-dashboard__content",
                ),
            ],
            className="map-dashboard__layout",
        ),
        dcc.Interval(id="map-refresh", interval=180 * 1000, n_intervals=0),
    ],
    className="map-dashboard",
)


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
    filtered_df = _apply_filters(
        df,
        search_text=search_text,
        operator=operator,
        province=province,
        municipality=municipality,
    )

    operator_options = _dropdown_options(sorted(_normalize_df(df)["Operator"].dropna().unique())) if not df.empty else []
    province_options = _dropdown_options(sorted(filtered_df["Province"].dropna().unique())) if not filtered_df.empty else []
    municipality_options = _dropdown_options(sorted(filtered_df["Municipality"].dropna().unique())) if not filtered_df.empty else []
    station_options = _dropdown_options(sorted(filtered_df["Station"].dropna().unique())) if not filtered_df.empty else []
    return operator_options, province_options, municipality_options, station_options, (err or "")


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
    filtered_df = _apply_filters(
        df,
        search_text=search_text,
        operator=operator,
        province=province,
        municipality=municipality,
        station=station,
    )

    selected_station = station
    if click_data and click_data.get("points"):
        point_data = click_data["points"][0].get("customdata") or []
        if point_data:
            selected_station = point_data[0]

    if filtered_df.empty:
        empty_message = err or "No stations available right now."
        return _build_empty_figure(empty_message), "0", "0", "0", _build_station_details(filtered_df, None)

    figure = _build_map_figure(filtered_df, selected_station)
    station_count = f"{len(filtered_df):,}"
    operator_count = f'{filtered_df["Operator"].replace("", None).dropna().nunique():,}'
    municipality_count = f'{filtered_df["Municipality"].replace("", None).dropna().nunique():,}'
    details = _build_station_details(filtered_df, selected_station)
    return figure, station_count, operator_count, municipality_count, details
