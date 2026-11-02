"""Dash-free helpers for the methodology page.

This module has no Dash dependency on purpose: CI installs only the
non-Dash test dependencies (pandas, requests, FastAPI, httpx, a2wsgi,
openlocationcode), so no test may import Dash or any module that
imports Dash. The rendering module, ``map_dashboard/metodologia.py``,
imports these helpers and turns their plain-text results into Dash
components. Tests import this module, never the rendering module.
"""

import dataset_meta

_SOURCE_STATUS_PT = {
    "loaded": "carregada",
    "stale_reused": "reutilizada depois de uma falha",
    "failed": "falhou nesta recolha",
}


def translate_source_status(status):
    return _SOURCE_STATUS_PT.get(status, status)


def format_meta_summary_pt(meta):
    """Return a short Portuguese summary of a metadata dict."""
    if meta is None or meta.get("generated_at") is None or meta.get("age_days") is None:
        return "Data de atualização indisponível."
    generated_at = dataset_meta._parse_generated_at(meta["generated_at"])
    if generated_at is None:
        return "Data de atualização indisponível."
    label = generated_at.strftime("%d/%m/%Y")
    age_days = meta["age_days"]
    status = meta["freshness_status"]
    record_count = meta.get("record_count")
    counts = f"{record_count} registos" if record_count is not None else "registos sem contagem publicada"
    if status == "overdue":
        state = "em atraso"
    elif status == "stale":
        state = "desatualizado"
    else:
        state = "atualizado"
    return (
        f"Snapshot de {label} (há {age_days} dias), com {counts}. "
        f"Estado de frescura: {state}."
    )


def source_status_lines(meta):
    """Return plain-text source-status lines for a metadata dict."""
    if meta is None:
        return ["Fonte e estado indisponíveis nesta altura."]
    lines = []
    for entry in meta.get("source_status", []):
        lines.append(
            f"{entry['source']}: {translate_source_status(entry['status'])} "
            f"({entry['record_count']} registos)"
            + (" (marcada como desatualizada)" if entry["is_stale"] else "")
        )
    if not lines:
        return ["Nenhuma fonte publicada neste snapshot."]
    return lines
