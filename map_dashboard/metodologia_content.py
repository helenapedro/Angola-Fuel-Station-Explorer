"""Dash-free helpers for the methodology page.

This module has no Dash dependency on purpose: CI installs only the
non-Dash test dependencies (pandas, requests, FastAPI, httpx, a2wsgi,
openlocationcode), so no test may import Dash or any module that
imports Dash. The rendering module, ``map_dashboard/metodologia.py``,
imports these helpers and turns their plain-text results into Dash
components. Tests import this module, never the rendering module.
"""

from datetime import datetime, timezone

import dataset_meta

_SOURCE_STATUS_PT = {
    "loaded": "carregada",
    "stale_reused": "reutilizada depois de uma falha",
    "failed": "falhou nesta recolha",
}

# Internal source names, shown in plain language on the methodology
# page. The API contract keeps the original names.
_SOURCE_NAMES_PT = {
    "BundledLegacyPumangol": "Snapshot anterior da Pumangol",
}


def translate_source_status(status):
    return _SOURCE_STATUS_PT.get(status, status)


def translate_source_name(source):
    return _SOURCE_NAMES_PT.get(source, source)


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


def version_lines(versions):
    """Return plain-text version-history lines for a registry list."""
    if not versions:
        return ["Nenhuma versão publicada foi registada ainda."]
    lines = []
    for entry in versions:
        generated_at = dataset_meta._parse_generated_at(entry.get("generated_at"))
        label = generated_at.strftime("%d/%m/%Y") if generated_at else "data indisponível"
        state = entry.get("freshness_status_at_publication") or "unknown"
        if state == "fresh":
            state_pt = "atualizado"
        elif state == "stale":
            state_pt = "desatualizado"
        elif state == "overdue":
            state_pt = "em atraso"
        else:
            state_pt = "estado de publicação desconhecido"
        lines.append(
            f"Versão {entry.get('version_id') or 'indisponível'}: snapshot de {label}, "
            f"{entry.get('record_count')} registos, {entry.get('rejected_count')} rejeitados, "
            f"estado na publicação: {state_pt}."
        )
    return lines


def overdue_note_pt(meta):
    """Return the dated overdue notice, or None when it does not apply.

    The notice states only verifiable facts (the snapshot age and the
    date it was checked) and the next step, which is a refresh. It
    never invents a cause for the delay: the cause and the owner's
    next step belong in a dated owner note, which is still pending.
    """
    if meta is None or meta.get("freshness_status") != "overdue":
        return None
    generated_at = dataset_meta._parse_generated_at(meta.get("generated_at"))
    if generated_at is None:
        return None
    return (
        f"Nota de atraso, verificada em {datetime.now(timezone.utc).strftime('%d/%m/%Y')}: "
        f"este snapshot, de {generated_at.strftime('%d/%m/%Y')}, tem mais de 28 dias. "
        "O próximo passo é uma nova recolha; até lá, trata estes dados como históricos, "
        "não como o estado atual da rede."
    )


def source_status_lines(meta):
    """Return plain-text source-status lines for a metadata dict."""
    if meta is None:
        return ["Fonte e estado indisponíveis nesta altura."]
    lines = []
    for entry in meta.get("source_status", []):
        lines.append(
            f"{translate_source_name(entry['source'])}: {translate_source_status(entry['status'])} "
            f"({entry['record_count']} registos)"
            + (" (marcada como desatualizada)" if entry["is_stale"] else "")
        )
    if not lines:
        return ["Nenhuma fonte publicada neste snapshot."]
    return lines
