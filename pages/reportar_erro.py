import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dcc, html
from datetime import datetime, timezone

import dataset_meta
import reports
from data_fetch import get_stations_df
from map_dashboard.data import apply_station_filters
from reports import (
    PROBLEM_TYPE_LABELS,
    Report,
    build_report_links,
    station_id_from_search,
    validate_report,
)

dash.register_page(__name__, path="/reportar-erro", name="Reportar erro", title="Reportar erro")


def _station_options(df):
    rows = df.sort_values("station")
    options = []
    for _, row in rows.iterrows():
        label = str(row.get("station"))
        operator = str(row.get("operator") or "").strip()
        if operator:
            label = f"{label} ({operator})"
        options.append({"label": label, "value": int(row["id"])})
    return options


def _station_summary(row):
    if row is None:
        return "Escolhe um posto para reportar um erro."
    def _field(value):
        text = str(value).strip() if value is not None else ""
        return text or "Não disponível"
    return html.Div(
        [
            html.H4(_field(row.get("station")), className="map-dashboard__detail-name"),
            html.Div(_field(row.get("operator")), className="map-dashboard__detail-brand"),
            html.Div(f"Morada: {_field(row.get('address'))}"),
            html.Div(f"Município: {_field(row.get('municipality'))} | Província: {_field(row.get('province'))}"),
            html.Div(f"Coordenadas: {row.get('latitude')}, {row.get('longitude')}"),
        ]
    )


layout = html.Div(
    [
        dcc.Location(id="report-url", refresh=False),
        html.Div("Reportar erro", className="metodologia__eyebrow"),
        html.H1("Reportar um erro num posto", className="metodologia__title"),
        html.P(
            "Indica o posto, o tipo de problema e, se souberes, uma fonte pública. "
            "O report só fica registado depois de submeteres a issue no GitHub. "
            "Não é pedido nenhum dado pessoal.",
            className="metodologia__copy",
        ),
        html.Div(id="report-snapshot", className="metodologia__snapshot"),
        dbc.Label("Posto", className="map-dashboard__label"),
        dcc.Dropdown(id="report-station-select", options=[], placeholder="Escolhe o posto"),
        dcc.Store(id="report-station-id", data=None),
        html.Div(id="report-station-summary", className="report-page__summary"),
        dbc.Label("Tipo de problema", className="map-dashboard__label"),
        dcc.Dropdown(
            id="report-problem-type",
            options=[
                {"label": label, "value": code}
                for code, label in PROBLEM_TYPE_LABELS.items()
            ],
            placeholder="Escolhe o tipo de problema",
        ),
        dbc.Label("Detalhes", className="map-dashboard__label"),
        dcc.Textarea(
            id="report-details",
            placeholder="Descreve o erro (opcional, máximo 500 caracteres)...",
            maxLength=500,
            className="map-dashboard__input map-dashboard__textarea",
        ),
        dbc.Label("Fonte pública (opcional)", className="map-dashboard__label"),
        dcc.Input(
            id="report-source-url",
            type="text",
            placeholder="https://...",
            className="map-dashboard__input",
        ),
        html.Button(
            "Gerar link para reportar",
            id="report-submit",
            n_clicks=0,
            className="map-dashboard__report-button",
        ),
        html.Div(id="report-output", className="map-dashboard__report-output"),
        html.Div(
            html.A("Voltar ao mapa", href="/", className="metodologia__link"),
            className="metodologia__back",
        ),
    ],
    className="report-page",
)


@callback(
    Output("report-station-select", "options"),
    Output("report-station-select", "value"),
    Output("report-snapshot", "children"),
    Input("report-url", "search"),
)
def init_report_page(search):
    df, _ = get_stations_df()
    normalized_df = apply_station_filters(df) if not df.empty else df
    meta = dataset_meta.load_dataset_meta(datetime.now(timezone.utc))
    if meta and meta.get("generated_at"):
        snapshot = (
            f"Snapshot: {meta['generated_at']} "
            f"(versão {meta.get('version_id') or meta['generated_at']})."
        )
    else:
        snapshot = "Data do snapshot indisponível."
    if normalized_df.empty or "id" not in normalized_df.columns:
        return [], None, snapshot
    station_id = station_id_from_search(search)
    value = station_id if station_id in set(normalized_df["id"]) else None
    return _station_options(normalized_df), value, snapshot


@callback(
    Output("report-station-id", "data"),
    Output("report-station-summary", "children"),
    Input("report-station-select", "value"),
)
def update_report_station(station_id):
    if station_id is None:
        return None, _station_summary(None)
    df, _ = get_stations_df()
    normalized_df = apply_station_filters(df) if not df.empty else df
    if normalized_df.empty or "id" not in normalized_df.columns:
        return None, _station_summary(None)
    rows = normalized_df[normalized_df["id"] == int(station_id)]
    if rows.empty:
        return None, _station_summary(None)
    return int(station_id), _station_summary(rows.iloc[0].to_dict())


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
