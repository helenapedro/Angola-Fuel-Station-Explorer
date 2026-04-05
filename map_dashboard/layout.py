"""Layout helpers for the station explorer dashboard."""

import dash_bootstrap_components as dbc
from dash import dcc, html


def build_dashboard_layout():
    return html.Div(
        [
            _build_hero_section(),
            html.Div(id="map-api-error", className="map-dashboard__error"),
            html.Div(
                [
                    _build_sidebar(),
                    _build_content_area(),
                ],
                className="map-dashboard__layout",
            ),
            dcc.Interval(id="map-refresh", interval=180 * 1000, n_intervals=0),
        ],
        className="map-dashboard",
    )


def _build_hero_section():
    return html.Div(
        [
            html.Div("Station Finder", className="map-dashboard__eyebrow"),
            html.H1("Explore fuel stations with the details you already have.", className="map-dashboard__title"),
            html.P(
                "Filter by operator, province, municipality, or station name and inspect location details directly from the map.",
                className="map-dashboard__subtitle",
            ),
        ],
        className="map-dashboard__hero",
    )


def _build_sidebar():
    return html.Div(
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
    )


def _build_content_area():
    return html.Div(
        [
            html.Div(
                [
                    _build_stat_card("Stations", "station-count"),
                    _build_stat_card("Brands", "operator-count"),
                    _build_stat_card("Municipalities", "municipality-count"),
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
    )


def _build_stat_card(label, value_id):
    return dbc.Card(
        dbc.CardBody(
            [
                html.Div(label, className="map-dashboard__stat-label"),
                html.Div(id=value_id, className="map-dashboard__stat-value"),
            ]
        ),
        className="map-dashboard__stat-card",
    )
