import dash
from dash import html
import dash_bootstrap_components as dbc
import os

app = dash.Dash(__name__, use_pages=True, external_stylesheets=[dbc.themes.SPACELAB])
server = app.server

navbar = dbc.Navbar(
    dbc.Container([
        dbc.NavbarBrand("Angola Fuel Station Explorer", href="/"),
        dbc.Nav(
            [
                dbc.NavLink("Map", href="/", active="exact"),
                dbc.NavLink("Table", href="/tabledata", active="exact"),
                dbc.NavLink("Stats", href="/stats", active="exact"),
            ],
            navbar=True,
        ),
    ]),
    color="#802917",
    dark=True,
)

footer = html.Footer(
    dbc.Container([
        html.Div([
            html.A("Helena Pedro", href="https://helenapedro.github.io/", target="_blank", style={"margin-right": "10px"}),
            html.Span("© 2024 | All rights reserved.")
        ], className="text-center"),
    ], fluid=True, className="py-3"),
    style={"background-color": "#802917", "color": "white"}
)

app.layout = dbc.Container([
    navbar,
    html.Hr(),
    dbc.Row(
        dbc.Col(dash.page_container, width={"size": 10, "offset": 1})
    ),
    html.Hr(),
    footer
], fluid=True)

if __name__ == "__main__":
    app.run(debug=os.getenv("DEBUG", "False").lower() == "true")
