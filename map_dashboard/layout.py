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
            _build_seo_content_section(),
            dcc.Interval(id="map-refresh", interval=180 * 1000, n_intervals=0),
        ],
        className="map-dashboard",
    )


def _build_hero_section():
    return html.Div(
        [
            html.Div("Localizador de postos", className="map-dashboard__eyebrow"),
            html.H1("Explora postos de combustível com os detalhes que já tens.", className="map-dashboard__title"),
            html.P(
                "Filtra por operador, província, município ou nome do posto e consulta os detalhes diretamente no mapa.",
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
                        html.Div("Filtros", className="map-dashboard__panel-title"),
                        dbc.Label("Pesquisar"),
                        dcc.Input(
                            id="map-search",
                            type="text",
                            placeholder="Pesquisar posto, morada, município...",
                            className="map-dashboard__input",
                        ),
                        dbc.Label("Marca", className="map-dashboard__label"),
                        dcc.Dropdown(id="operator-filter", options=[], placeholder="Todas as marcas"),
                        dbc.Label("Província", className="map-dashboard__label"),
                        dcc.Dropdown(id="province-filter", options=[], placeholder="Todas as províncias"),
                        dbc.Label("Município", className="map-dashboard__label"),
                        dcc.Dropdown(id="municipality-filter", options=[], placeholder="Todos os municípios"),
                        dbc.Label("Posto", className="map-dashboard__label"),
                        dcc.Dropdown(id="station-filter", options=[], placeholder="Todos os postos"),
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
            # Dataset freshness badge: deliberately in the content area,
            # directly above the counters, not in the footer, so a stale
            # or overdue snapshot is visible with the map.
            html.Div(id="dataset-updated-badge", className="map-dashboard__dataset-badge"),
            html.Div(
                [
                    _build_stat_card("Postos", "station-count"),
                    _build_stat_card("Marcas", "operator-count"),
                    _build_stat_card("Províncias", "province-count"),
                    _build_stat_card("Municípios", "municipality-count"),
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


def _build_seo_content_section():
    return html.Section(
        [
            html.H2("Encontrar postos de combustível em Angola", className="map-dashboard__seo-title"),
            html.P(
                "O FuelMap Angola ajuda a encontrar postos de combustível em Angola com um mapa interativo e um diretório de postos pesquisável.",
                className="map-dashboard__seo-copy",
            ),
            html.P(
                "Usa o painel para pesquisar postos por marca, província, município e nome do posto. A aplicação apoia a descoberta de postos em Angola, incluindo Luanda e outras províncias.",
                className="map-dashboard__seo-copy",
            ),
            html.P(
                "Se procuras postos de gasolina em Angola, postos de combustível em Luanda ou um localizador de postos para Angola, esta ferramenta foi feita para tornar esses locais mais fáceis de consultar.",
                className="map-dashboard__seo-copy",
            ),
        ],
        className="map-dashboard__seo-section",
    )
