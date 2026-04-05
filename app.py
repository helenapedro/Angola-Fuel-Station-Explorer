import os

import dash
import dash_bootstrap_components as dbc
from flask import Response
from dash import html

from seo import SITE_DESCRIPTION, SITE_TITLE, build_meta_tags, build_robots_txt, build_sitemap_xml

app = dash.Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[dbc.themes.SPACELAB],
    meta_tags=build_meta_tags(),
    title=SITE_TITLE,
)
server = app.server


@server.route("/robots.txt")
def robots_txt():
    return Response(build_robots_txt(), mimetype="text/plain")


@server.route("/sitemap.xml")
def sitemap_xml():
    return Response(build_sitemap_xml(), mimetype="application/xml")

navbar = dbc.Navbar(
    dbc.Container([
        dbc.NavbarBrand("Angola Fuel Station Explorer", href="/"),
    ]),
    color="#802917",
    dark=True,
)

footer = html.Footer(
    dbc.Container([
        html.Div([
            html.A("Helena Pedro", href="https://helenapedro.github.io/", target="_blank", style={"margin-right": "10px"}),
            html.Span("(c) 2024 | All rights reserved."),
        ], className="text-center"),
    ], fluid=True, className="py-3"),
    style={"background-color": "#802917", "color": "white"},
)

app.layout = dbc.Container([
    navbar,
    html.Div(
        [
            html.H1(SITE_TITLE, style={"display": "none"}),
            html.P(SITE_DESCRIPTION, style={"display": "none"}),
        ],
        style={"display": "none"},
    ),
    html.Hr(),
    dbc.Row(
        dbc.Col(dash.page_container, width={"size": 10, "offset": 1})
    ),
    html.Hr(),
    footer,
], fluid=True)

if __name__ == "__main__":
    app.run(debug=os.getenv("DEBUG", "False").lower() == "true")
