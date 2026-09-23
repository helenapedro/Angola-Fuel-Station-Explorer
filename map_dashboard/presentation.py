"""Presentation helpers for the station explorer dashboard."""

import plotly.express as px
from dash import html

MAP_HEIGHT = 680
EMPTY_FIGURE_CENTER = {"lat": -11.2027, "lon": 17.8739}

# Stable brand colors so the map legend is consistent across reloads and
# filters. Unknown (bandeira-branca independents) stays neutral gray.
OPERATOR_COLORS = {
    "Sonangol": "#D7263D",
    "Pumangol": "#F46036",
    "TotalEnergies": "#1B4F9C",
    "Sonangalp": "#F18F01",
    "Etu Energias": "#2A9D48",
    "Unknown": "#9E9E9E",
}


def build_empty_figure(message):
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


def build_map_figure(filtered_df, selected_station):
    if filtered_df.empty:
        return build_empty_figure("No stations match the current filters.")

    center = {
        "lat": filtered_df["latitude"].mean(),
        "lon": filtered_df["longitude"].mean(),
    }
    zoom = 5 if len(filtered_df) > 1 else 11

    fig = px.scatter_mapbox(
        filtered_df,
        lat="latitude",
        lon="longitude",
        color="operator",
        color_discrete_map=OPERATOR_COLORS,
        hover_name="station",
        hover_data={
            "operator": True,
            "municipality": True,
            "province": True,
            "address": True,
            "latitude": False,
            "longitude": False,
        },
        custom_data=["station", "operator", "municipality", "province", "address", "country"],
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
        selected_row = filtered_df[filtered_df["station"] == selected_station]
        if not selected_row.empty:
            fig.add_scattermapbox(
                lat=selected_row["latitude"],
                lon=selected_row["longitude"],
                mode="markers",
                marker={"size": 20, "color": "#f4a261", "opacity": 1},
                hoverinfo="skip",
                showlegend=False,
            )

    return fig


def build_station_details(filtered_df, selected_station):
    if filtered_df.empty:
        return html.Div(
            "No station available for the current filters.",
            className="map-dashboard__detail-empty",
        )

    station_row = filtered_df.iloc[0]
    if selected_station:
        selected_rows = filtered_df[filtered_df["station"] == selected_station]
        if not selected_rows.empty:
            station_row = selected_rows.iloc[0]

    # Brand is already the panel header; the rows below start at the name.
    items = [
        ("station", station_row.get("station")),
        ("address", station_row.get("address")),
        ("municipality", station_row.get("municipality")),
        ("province", station_row.get("province")),
        ("country", station_row.get("country")),
        ("Coordinates", f'{station_row.get("latitude")}, {station_row.get("longitude")}'),
    ]

    return html.Div(
        [
            html.Div("Selected Station", className="map-dashboard__panel-title"),
            html.H4(_safe_text(station_row.get("station")), className="map-dashboard__detail-name"),
            html.Div(_safe_text(station_row.get("operator")), className="map-dashboard__detail-brand"),
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


def _safe_text(value, fallback="Not available"):
    if value is None:
        return fallback
    text = str(value).strip()
    return text if text else fallback
