import dash
from dash import Input, Output, State, callback, dash_table, dcc, html
import pandas as pd

from data_fetch import get_stations_df

dash.register_page(__name__, path="/tabledata", name="Table Data", title="Table")

TABLE_COLUMNS = [
    {"name": "Operator", "id": "Operator", "deletable": True},
    {"name": "Station", "id": "Station", "deletable": True},
    {"name": "Address", "id": "Address", "deletable": True},
    {"name": "Municipality", "id": "Municipality", "deletable": True},
    {"name": "Latitude", "id": "Latitude", "deletable": True},
    {"name": "Longitude", "id": "Longitude", "deletable": True},
    {"name": "Province", "id": "Province", "deletable": True},
    {"name": "Country", "id": "Country", "deletable": True},
]


layout = html.Div([
    html.Div(id="table-page-api-error", style={"color": "#800000", "marginBottom": "10px"}),
    dcc.Dropdown(
        id="table-page-municipality-dropdown",
        options=[],
        placeholder="Select a Municipality",
    ),
    html.Span("Copy selected "),
    dcc.Clipboard(id="table-page-clipboard", style={"display": "inline-block"}),
    dash_table.DataTable(
        id="table-page-table",
        columns=TABLE_COLUMNS,
        style_table={"height": "500px", "overflowY": "auto"},
        style_cell={"padding": "10px", "textAlign": "center"},
        style_header={"backgroundColor": "rgb(230, 230, 230)", "fontWeight": "bold"},
        row_selectable="multi",
        selected_rows=[],
        page_action="native",
        page_size=25,
        export_format="csv",
    ),
    dcc.Interval(id="table-page-refresh", interval=180 * 1000, n_intervals=0),
])


@callback(
    Output("table-page-municipality-dropdown", "options"),
    Output("table-page-api-error", "children"),
    Input("table-page-refresh", "n_intervals"),
)
def refresh_filters(_):
    df, err = get_stations_df()
    if df.empty or "Municipality" not in df:
        return [], (err or "")

    municipalities = sorted(df["Municipality"].dropna().unique())
    options = [{"label": municipality, "value": municipality} for municipality in municipalities]
    return options, (err or "")


@callback(
    Output("table-page-table", "data"),
    Input("table-page-municipality-dropdown", "value"),
    Input("table-page-refresh", "n_intervals"),
)
def update_table(selected_municipality, _):
    df, _err = get_stations_df()
    if df.empty:
        return []

    if selected_municipality:
        df = df[df["Municipality"] == selected_municipality]

    return df.to_dict("records")


@callback(
    Output("table-page-clipboard", "content"),
    Input("table-page-table", "selected_rows"),
    State("table-page-table", "data"),
)
def copy_selected_rows(selected_rows, data):
    if not selected_rows:
        return "No selections"

    selected_data = [data[i] for i in selected_rows]
    df_selected = pd.DataFrame(selected_data)
    return df_selected.to_string()
