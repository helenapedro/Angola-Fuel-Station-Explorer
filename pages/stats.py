import dash
import plotly.express as px
from dash import Input, Output, callback, dcc, html

from data_fetch import get_stations_df

dash.register_page(__name__, path="/stats", name="Statistics", title="Stats")


layout = html.Div([
    html.Div([
        html.Div(id="stats-page-api-error", style={"color": "#800000", "marginBottom": "10px"}),
        html.Div(id="stats-page-total-gas-stations", style={"fontSize": "24px", "fontWeight": "bold", "marginBottom": "20px"}),
        html.Div(id="stats-page-additional-statistics", style={"fontSize": "18px", "marginBottom": "20px"}),
        html.Div([
            html.Div([
                html.Label("Select Province:"),
                dcc.Dropdown(id="stats-page-province-dropdown", style={"width": "100%"}),
            ], style={"flex": "1", "paddingRight": "10px"}),
            html.Div([
                html.Label("Select Municipality:"),
                dcc.Dropdown(id="stats-page-municipality-dropdown", style={"width": "100%"}),
            ], style={"flex": "1"}),
        ], style={"display": "flex", "justifyContent": "space-between", "marginBottom": "20px"}),
        html.Div([
            html.Div([dcc.Graph(id="stats-page-municipality-distribution")], style={"marginBottom": "20px"}),
            html.Div([dcc.Graph(id="stats-page-operator-distribution")], style={"marginBottom": "20px"}),
        ]),
    ], style={"maxWidth": "1200px", "margin": "0 auto", "padding": "20px"}),
    dcc.Interval(id="stats-page-refresh", interval=180 * 1000, n_intervals=0),
])


@callback(
    Output("stats-page-province-dropdown", "options"),
    Output("stats-page-api-error", "children"),
    Input("stats-page-refresh", "n_intervals"),
)
def update_province_dropdown(_):
    df, err = get_stations_df()
    if df.empty or "Province" not in df:
        return [], (err or "")

    provinces = sorted(df["Province"].dropna().unique())
    return [{"label": province, "value": province} for province in provinces], (err or "")


@callback(
    Output("stats-page-municipality-dropdown", "options"),
    Input("stats-page-province-dropdown", "value"),
    Input("stats-page-refresh", "n_intervals"),
)
def update_municipality_dropdown(selected_province, _):
    df, _err = get_stations_df()
    if not selected_province or df.empty or "Province" not in df or "Municipality" not in df:
        return []

    municipalities = sorted(
        df.loc[df["Province"] == selected_province, "Municipality"].dropna().unique()
    )
    return [{"label": municipality, "value": municipality} for municipality in municipalities]


@callback(
    Output("stats-page-total-gas-stations", "children"),
    Output("stats-page-additional-statistics", "children"),
    Output("stats-page-operator-distribution", "figure"),
    Output("stats-page-municipality-distribution", "figure"),
    Input("stats-page-province-dropdown", "value"),
    Input("stats-page-municipality-dropdown", "value"),
    Input("stats-page-refresh", "n_intervals"),
)
def update_graph(selected_province, selected_municipality, _):
    df, err = get_stations_df()
    if df.empty:
        return (err or "Unable to fetch data"), "", {}, {}

    filtered_df = df
    if selected_province:
        filtered_df = filtered_df[filtered_df["Province"] == selected_province]
    if selected_municipality:
        filtered_df = filtered_df[filtered_df["Municipality"] == selected_municipality]

    total_gas_stations = len(filtered_df)
    num_operators = filtered_df["Operator"].nunique()
    num_municipalities = filtered_df["Municipality"].nunique()
    additional_stats = f"Unique Operators: {num_operators} | Unique Municipalities: {num_municipalities}"

    operator_counts = filtered_df["Operator"].value_counts()
    operator_fig = px.bar(
        operator_counts,
        x=operator_counts.index,
        y=operator_counts.values,
        labels={"x": "Operator", "y": "Count"},
        title="Operator Distribution",
    )

    municipality_counts = filtered_df["Municipality"].value_counts()
    municipality_fig = px.bar(
        municipality_counts,
        x=municipality_counts.index,
        y=municipality_counts.values,
        labels={"x": "Municipality", "y": "Count"},
        title="Municipality Distribution",
    )

    return f"Total Gas Stations: {total_gas_stations}", additional_stats, operator_fig, municipality_fig
