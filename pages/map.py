import dash
from dash import Input, Output, State, callback, html
from datetime import datetime, timezone

import dataset_meta
import reports
from data_fetch import get_stations_df
from reports import Report, build_report_links, validate_report
from map_dashboard.data import (
    apply_station_filters,
    build_filter_options,
    build_summary_counts,
    get_selected_station_name,
)
from map_dashboard.layout import build_dashboard_layout
from map_dashboard.presentation import build_empty_figure, build_map_figure, build_station_details

dash.register_page(__name__, path="/", name="Mapa", title="Início")

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
    Output("dataset-updated-badge", "children"),
    Output("dataset-updated-badge", "className"),
    Input("map-refresh", "n_intervals"),
)
def update_dataset_badge(_):
    meta = dataset_meta.load_dataset_meta(datetime.now(timezone.utc))
    text, status = dataset_meta.format_dataset_badge(meta)
    return text, f"map-dashboard__dataset-badge map-dashboard__dataset-badge--{status}"


@callback(
    Output("gas-stations-map", "figure"),
    Output("station-count", "children"),
    Output("operator-count", "children"),
    Output("province-count", "children"),
    Output("municipality-count", "children"),
    Output("selected-station-card", "children"),
    Output("report-station-id", "data"),
    Output("report-card", "style"),
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
        empty_message = err or "Nenhum posto disponível neste momento."
        return (
            build_empty_figure(empty_message),
            "0",
            "0",
            "0",
            "0",
            build_station_details(filtered_df, None),
            None,
            {"display": "none"},
        )

    station_count, operator_count, province_count, municipality_count = build_summary_counts(filtered_df)
    station_row = filtered_df.iloc[0]
    if selected_station:
        selected_rows = filtered_df[filtered_df["station"] == selected_station]
        if not selected_rows.empty:
            station_row = selected_rows.iloc[0]
    station_id = station_row.get("id") if "id" in station_row else None
    return (
        build_map_figure(filtered_df, selected_station),
        station_count,
        operator_count,
        province_count,
        municipality_count,
        build_station_details(filtered_df, selected_station),
        int(station_id) if station_id is not None else None,
        {"display": "block"},
    )


@callback(
    Output("report-output", "children"),
    Input("report-submit", "n_clicks"),
    State("report-station-id", "data"),
    State("report-problem-type", "value"),
    State("report-details", "value"),
    State("report-source-url", "value"),
    prevent_initial_call=True,
)
def submit_report(_, station_id, problem_type, details, source_url):
    """Validate a report and generate the pre-filled issue link.

    Nothing is stored: an invalid report generates no link, and a
    valid report only produces a link for the user to review and
    submit on GitHub. The station is re-derived from the current
    dataset, never trusted from the form alone.
    """
    df, err = get_stations_df()
    # The raw frame has no stable id; normalise it exactly as the
    # dashboard view does, so validation uses the same ids.
    normalized_df = apply_station_filters(df) if not df.empty else df
    if err or normalized_df.empty or "id" not in normalized_df.columns:
        return "Não foi possível validar o posto neste momento. Não foi gerado nenhum link."
    report = Report(
        station_id=station_id,
        problem_type=problem_type or "",
        details=details or "",
        source_url=source_url or "",
    )
    errors = validate_report(report, set(normalized_df["id"]))
    if errors:
        return html.Div(
            [html.Div(error, className="map-dashboard__report-error") for error in errors]
        )
    station_row = normalized_df[normalized_df["id"] == int(report.station_id)]
    if station_row.empty:
        return "A estação não foi encontrada no dataset atual. Não foi gerado nenhum link."
    meta = dataset_meta.load_dataset_meta(datetime.now(timezone.utc))
    if meta and meta.get("generated_at"):
        version_id = meta.get("version_id") or meta["generated_at"]
        generated_at = meta["generated_at"]
    else:
        version_id = "indisponível"
        generated_at = "indisponível"
    links = build_report_links(
        report,
        station_row.iloc[0].to_dict(),
        version_id,
        generated_at,
        form_url=reports.REPORT_FORM_URL,
    )
    children = [
        html.Div(
            "Revê e submete no GitHub. O report só fica registado depois de submeteres a issue.",
            className="map-dashboard__report-success",
        ),
        html.A(
            "Rever e submeter no GitHub",
            href=links["github_url"],
            target="_blank",
            className="map-dashboard__report-link",
        ),
    ]
    if links.get("form_url"):
        children.append(
            html.A(
                "Reportar sem conta (formulário)",
                href=links["form_url"],
                target="_blank",
                className="map-dashboard__report-link",
            )
        )
    return html.Div(children)
