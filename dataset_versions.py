"""Dataset version registry for the FuelMap Angola.

Git is the source of truth: the ingestion workflow appends one entry to
``data/dataset_versions.json`` in the same commit that updates
``data/stations_clean.json``. Entries are immutable once committed; a
wrong number is corrected in a later version, never by rewriting an
old entry. ``version_id`` is exactly ``generated_at``: deterministic,
verifiable from the file, and already the ingestion idempotency key.

Standard library only, so the ingestion workflow (which installs only
``requests`` and ``openlocationcode``) and the CI environment (which
has no Dash) can both use this module.

Confidence derivation, from the raw per-station fields that already
exist in the snapshot: ``operator_website`` is ``operador_via_listagem_publica``
(found in a public listing on the operator's website at ``scraped_at``,
not supplied under an agreement); ``openstreetmap_operator`` is
``operador_via_osm``; anything else is ``base_publica_osm``. A record
marked ``is_stale`` keeps its base level; staleness is reported through
``source_status``, not by changing the level. The counts are computed
over the clean records only, so they always sum to ``record_count``.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from dataset_meta import (
    FRESH_THRESHOLD_DAYS,
    OVERDUE_THRESHOLD_DAYS,
    SNAPSHOT_ORIGIN,
)

CONFIDENCE_LEVEL_OPERATOR_LISTING = "operador_via_listagem_publica"
CONFIDENCE_LEVEL_OSM_OPERATOR = "operador_via_osm"
CONFIDENCE_LEVEL_BASE = "base_publica_osm"
CONFIDENCE_LEVELS = (
    CONFIDENCE_LEVEL_OPERATOR_LISTING,
    CONFIDENCE_LEVEL_OSM_OPERATOR,
    CONFIDENCE_LEVEL_BASE,
)

VERSIONS_PATH = Path(__file__).parent / "data" / "dataset_versions.json"


def confidence_level(record):
    """Return the confidence level for one raw station record."""
    source_type = record.get("source_type") if isinstance(record, dict) else None
    if source_type == "operator_website":
        return CONFIDENCE_LEVEL_OPERATOR_LISTING
    if source_type == "openstreetmap_operator":
        return CONFIDENCE_LEVEL_OSM_OPERATOR
    return CONFIDENCE_LEVEL_BASE


def confidence_counts(records):
    """Count clean records by confidence level; the sum is len(records)."""
    counts = {level: 0 for level in CONFIDENCE_LEVELS}
    for record in records:
        counts[confidence_level(record)] += 1
    return counts


def freshness_status_at(generated_at, now):
    """Freshness status of a snapshot at a given moment, or "unknown"."""
    if generated_at is None or now is None:
        return "unknown"
    try:
        generated = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return "unknown"
    if generated.tzinfo is None:
        generated = generated.replace(tzinfo=timezone.utc)
    if generated > now:
        return "unknown"
    age_days = (now - generated).days
    if age_days <= FRESH_THRESHOLD_DAYS:
        return "fresh"
    if age_days <= OVERDUE_THRESHOLD_DAYS:
        return "stale"
    return "overdue"


def _sanitise_source_status(entries):
    sanitised = []
    for entry in entries or []:
        if not isinstance(entry, dict):
            continue
        sanitised.append(
            {
                "source": entry.get("source"),
                "status": entry.get("status"),
                "record_count": entry.get("record_count", 0),
                "is_stale": bool(entry.get("is_stale", False)),
            }
        )
    return sanitised


def build_version_entry(meta, now=None):
    """Build one immutable version entry from a metadata dict."""
    now = now or datetime.now(timezone.utc)
    generated_at = meta.get("generated_at") if isinstance(meta, dict) else None
    return {
        "version_id": generated_at,
        "snapshot_origin": SNAPSHOT_ORIGIN,
        "generated_at": generated_at,
        "record_count": meta.get("record_count"),
        "rejected_count": meta.get("rejected_count"),
        "freshness_status_at_publication": freshness_status_at(generated_at, now),
        "source_status_summary": _sanitise_source_status(
            meta.get("source_status") if isinstance(meta, dict) else None
        ),
    }


def append_version_entry(versions, meta, now=None):
    """Append an entry unless its version_id is already present.

    Existing entries are returned unchanged, in order. This is what
    makes the registry append-only and the append idempotent on
    ``generated_at``: re-running the workflow step for the same
    snapshot never rewrites history or duplicates the entry.
    """
    versions = list(versions or [])
    entry = build_version_entry(meta, now=now)
    if entry["version_id"] is None:
        return versions, entry, False
    if any(v.get("version_id") == entry["version_id"] for v in versions):
        return versions, entry, False
    return versions + [entry], entry, True


def load_dataset_versions(versions_path=None, meta=None, now=None):
    """Load the version registry, falling back to the current snapshot.

    A missing or unreadable versions file never fails the caller: a
    single entry derived from the current metadata is returned, with
    ``freshness_status_at_publication`` set to ``"unknown"`` so the
    fallback is visibly not a recorded publication. With no metadata
    either, the list is empty.
    """
    path = Path(versions_path) if versions_path is not None else VERSIONS_PATH
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        payload = None
    if isinstance(payload, list) and payload:
        return payload
    if meta is None:
        return []
    entry = build_version_entry(meta, now=now)
    entry["freshness_status_at_publication"] = "unknown"
    return [entry]


def read_versions_file(versions_path=None):
    """Return the recorded entries, or an empty list if none exist."""
    path = Path(versions_path) if versions_path is not None else VERSIONS_PATH
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return payload if isinstance(payload, list) else []
