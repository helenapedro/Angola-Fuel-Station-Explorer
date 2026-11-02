import dash
from dash import Input, Output, callback, html
from datetime import datetime, timezone

import dataset_meta
from map_dashboard.metodologia import (
    build_metodologia_layout,
    build_source_status_items,
    format_meta_summary_pt,
)

dash.register_page(__name__, path="/metodologia", name="Metodologia", title="Metodologia")

layout = build_metodologia_layout()


@callback(
    Output("metodologia-meta", "children"),
    Output("metodologia-source-status", "children"),
    Input("metodologia-refresh", "n_intervals"),
)
def update_metodologia_snapshot(_):
    meta = dataset_meta.load_dataset_meta(datetime.now(timezone.utc))
    summary = format_meta_summary_pt(meta)
    if meta is None:
        return summary, html.Ul(
            [html.Li("Fonte e estado indisponíveis nesta altura.")]
        )
    return summary, html.Ul(build_source_status_items(meta))
