import dash
from dash import Input, Output, callback, html
from datetime import datetime, timezone

import dataset_meta
import dataset_versions
from map_dashboard.metodologia import (
    build_metodologia_layout,
    build_source_status_items,
    build_version_items,
)
from map_dashboard.metodologia_content import format_meta_summary_pt, overdue_note_pt

dash.register_page(__name__, path="/metodologia", name="Metodologia", title="Metodologia")

layout = build_metodologia_layout()


@callback(
    Output("metodologia-meta", "children"),
    Output("metodologia-source-status", "children"),
    Output("metodologia-versions", "children"),
    Output("metodologia-overdue-note", "children"),
    Input("metodologia-refresh", "n_intervals"),
)
def update_metodologia_snapshot(_):
    meta = dataset_meta.load_dataset_meta(datetime.now(timezone.utc))
    summary = format_meta_summary_pt(meta)
    versions = dataset_versions.load_dataset_versions(meta=meta)
    versions_children = html.Ul(build_version_items(versions))
    note = overdue_note_pt(meta)
    overdue_children = html.P(note, className="metodologia__copy") if note else ""
    if meta is None:
        return (
            summary,
            html.Ul([html.Li("Fonte e estado indisponíveis nesta altura.")]),
            versions_children,
            overdue_children,
        )
    return summary, html.Ul(build_source_status_items(meta)), versions_children, overdue_children
