"""Error reports: pure validation and pre-filled issue URL building.

Phase 0, design section 8.3 and 10.5. A report is never stored on the
server: the dashboard only generates a link to a pre-filled GitHub
Issue, and the report only exists once the user submits that issue.
No file writes, no token, no network call to GitHub from the server,
no personal data (no name, email, phone or user location).

The no-account form is the planned primary path (Helena's decision,
2026-11-01), but the form does not exist yet and Helena deferred
creating it. ``REPORT_FORM_URL`` stays ``None`` until she supplies
the form URL; the callback then shows only the GitHub link. Wiring
the form later is setting this one constant, plus pre-fill
parameters if the form supports them. No URL is invented here.
"""

import re
from dataclasses import dataclass, field
from urllib.parse import parse_qs, urlencode, urlparse

ISSUE_NEW_URL = "https://github.com/helenapedro/fuelmap-angola/issues/new"

# No-account report form URL, supplied by Helena when she creates the
# form. None until then: only the GitHub path is shown.
REPORT_FORM_URL = None

PROBLEM_TYPES = (
    "posto_fechado",
    "morada_errada",
    "coordenadas_erradas",
    "operador_errado",
    "posto_em_falta",
    "outro",
)

PROBLEM_TYPE_LABELS = {
    "posto_fechado": "Posto fechado",
    "morada_errada": "Morada errada",
    "coordenadas_erradas": "Coordenadas erradas",
    "operador_errado": "Operador errado",
    "posto_em_falta": "Posto em falta",
    "outro": "Outro",
}

MAX_DETAILS_CHARS = 500

_HTML_TAG_RE = re.compile(r"<[^>]*>")


def strip_html_tags(text):
    """Remove HTML tags from free text, before validation."""
    return _HTML_TAG_RE.sub("", text or "")


@dataclass
class Report:
    """A validated-or-to-be-validated error report.

    ``station_id`` is the stable integer station id from
    :func:`station_data.stable_station_id`, not a row number and not
    a station name (names repeat across operators and locations).
    """

    station_id: object
    problem_type: str = ""
    details: str = ""
    source_url: str = ""
    errors: list = field(default_factory=list, init=False)


def station_id_from_search(search):
    """Return the station id from a URL query string, or None.

    ``search`` is the ``dcc.Location`` search value, for example
    ``"?station_id=123"``. Only the first value counts; anything
    missing, empty or non-numeric returns None, never an invented id.
    """
    if not search:
        return None
    values = parse_qs(urlparse(search).query if "?" in search else search).get("station_id")
    if not values:
        return None
    return _normalise_station_id(values[0])


def _normalise_station_id(value):
    try:
        if isinstance(value, bool):
            return None
        return int(str(value).strip())
    except (TypeError, ValueError, AttributeError):
        return None


def validate_report(report, known_station_ids):
    """Validate a report against the current dataset.

    HTML is stripped from ``details`` first, so tags neither count
    towards the 500-character limit nor reach the issue body.
    ``source_url`` is stripped of surrounding whitespace; an empty
    value means no source was indicated. Returns a list of
    Portuguese error messages; an empty list means valid. The
    report's ``details`` and ``source_url`` are replaced by their
    cleaned forms, and ``report.errors`` is set to the result.
    """
    report.details = strip_html_tags(report.details or "").strip()
    report.source_url = (report.source_url or "").strip()

    errors = []
    station_id = _normalise_station_id(report.station_id)
    if station_id is None or station_id not in set(known_station_ids):
        errors.append("A estação não existe no dataset atual.")
    if (report.problem_type or "") not in PROBLEM_TYPES:
        errors.append("O tipo de problema é inválido.")
    if len(report.details) > MAX_DETAILS_CHARS:
        errors.append("Os detalhes excedem 500 caracteres.")
    if report.source_url:
        if not report.source_url.startswith("https://"):
            errors.append("A fonte indicada tem de começar por https://.")
        elif any(ch.isspace() for ch in report.source_url):
            errors.append("A fonte indicada não pode conter espaços.")
    report.errors = errors
    return errors


def _safe_field(value):
    text = str(value).strip() if value is not None else ""
    return text or "Não disponível"


def build_issue_body(report, station, version_id, dataset_generated_at):
    """Build the fixed issue body tying a correction to a snapshot.

    ``station`` is a mapping (or row) with station, operator,
    municipality, province, latitude and longitude. Coordinates are
    included so a report can be triaged even when station names
    repeat. ``version_id`` and ``dataset_generated_at`` are never
    invented: pass "indisponível" when the metadata is unavailable.
    """
    return "\n".join(
        [
            f"Estação: {report.station_id} - {_safe_field(station.get('station'))} "
            f"({_safe_field(station.get('operator'))}, "
            f"{_safe_field(station.get('municipality'))}, "
            f"{_safe_field(station.get('province'))})",
            f"Coordenadas: {station.get('latitude')}, {station.get('longitude')}",
            f"Versão do dataset: {version_id}",
            f"Gerado em: {dataset_generated_at}",
            f"Tipo de problema: {report.problem_type}",
            f"Detalhes: {report.details or 'Sem detalhes'}",
            f"Fonte indicada: {report.source_url or 'Nenhuma'}",
        ]
    )


def build_issue_url(report, station, version_id, dataset_generated_at):
    """Return the pre-filled GitHub Issue URL for a validated report."""
    title = f"[correção de dados] Estação {report.station_id}: {report.problem_type}"
    query = urlencode(
        {
            "title": title,
            "body": build_issue_body(report, station, version_id, dataset_generated_at),
            "labels": f"data-correction,{report.problem_type}",
        }
    )
    return f"{ISSUE_NEW_URL}?{query}"


def build_report_links(report, station, version_id, dataset_generated_at, form_url=None):
    """Return the links to show for a validated report.

    Always the GitHub issue link. The no-account form link is added
    only when ``form_url`` is set; no pre-fill parameters are
    invented for a form that does not exist yet.
    """
    links = {
        "github_url": build_issue_url(report, station, version_id, dataset_generated_at),
    }
    if form_url:
        links["form_url"] = form_url
    return links
