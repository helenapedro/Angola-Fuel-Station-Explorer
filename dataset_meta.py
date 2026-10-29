"""Dataset metadata for the Angola Fuel Station Explorer.

This module is the single source of truth for dataset freshness in
Phase 0. Both the FastAPI ``/api/v1/meta`` endpoint and the Dash
"Updated on" badge call :func:`load_dataset_meta` directly, so the UI
and the API cannot drift apart.

The metadata comes from the ``metadata`` block of the bundled
``data/stations_clean.json`` snapshot. It is deliberately *not* derived
from the Dash DataFrame (which drops metadata), from the cache TTL
(300 seconds, which is a request cache, not a dataset age), or from
the deploy date.

If the snapshot file is missing, unreadable, or has no ``metadata``
block, :func:`load_dataset_meta` returns ``None``. Callers must then
show "unavailable", never an invented date. If ``generated_at`` itself
is missing, unparseable, or in the future, the returned dict has
``age_days=None`` and ``freshness_status="unavailable"``.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

CACHE_TTL_SECONDS = 300
FRESH_THRESHOLD_DAYS = 14
OVERDUE_THRESHOLD_DAYS = 28
CLEAN_DATA_PATH = Path(__file__).parent / "data" / "stations_clean.json"
SNAPSHOT_ORIGIN = (
    "helenapedro/Angola-Fuel-Station-Explorer:data/stations_clean.json"
)

_CACHE = {"path": None, "metadata": None, "loaded_at": None}


def clear_dataset_meta_cache() -> None:
    """Clear the in-memory metadata cache (used by tests)."""
    _CACHE.update({"path": None, "metadata": None, "loaded_at": None})


def freshness_status(age_days):
    """Derive the public freshness status from an age in days."""
    if age_days is None:
        return "unavailable"
    if age_days <= FRESH_THRESHOLD_DAYS:
        return "fresh"
    if age_days <= OVERDUE_THRESHOLD_DAYS:
        return "stale"
    return "overdue"


def _parse_generated_at(raw):
    """Parse an ISO 8601 timestamp, or return None if it is unusable."""
    if not isinstance(raw, str) or not raw.strip():
        return None
    text = raw.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _sanitise_source_status(entries):
    """Return only public source-status fields.

    Detailed error messages stay in the ingestion logs and in the
    snapshot file; they are never exposed through the public API.
    """
    if not isinstance(entries, list):
        return []
    sanitised = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if "source" not in entry or "status" not in entry:
            continue
        sanitised.append(
            {
                "source": entry["source"],
                "status": entry["status"],
                "record_count": entry.get("record_count", 0),
                "is_stale": bool(entry.get("is_stale", False)),
            }
        )
    return sanitised


def _as_int(value):
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def load_dataset_meta(now=None, data_path=None):
    """Return the normalised dataset metadata, or None if unavailable.

    ``now`` defaults to the current UTC time. ``data_path`` defaults to
    the bundled snapshot and exists mainly so tests can point at a
    fixture without touching the real dataset.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    path = Path(data_path) if data_path is not None else CLEAN_DATA_PATH

    cached = _CACHE["metadata"]
    loaded_at = _CACHE["loaded_at"]
    if (
        cached is not None
        and _CACHE["path"] == str(path)
        and loaded_at is not None
        and (now - loaded_at).total_seconds() < CACHE_TTL_SECONDS
    ):
        return cached

    try:
        with path.open("r", encoding="utf-8") as data_file:
            payload = json.load(data_file)
        raw_meta = payload["metadata"]
        if not isinstance(raw_meta, dict):
            raise ValueError("metadata must be an object")
    except (OSError, ValueError, KeyError, TypeError):
        return None

    raw_generated_at = raw_meta.get("generated_at")
    generated_at = _parse_generated_at(raw_generated_at)
    if generated_at is None or generated_at > now:
        freshness = {
            "age_days": None,
            "fresh": False,
            "is_stale": None,
            "freshness_status": "unavailable",
        }
    else:
        age_days = (now - generated_at).days
        status = freshness_status(age_days)
        freshness = {
            "age_days": age_days,
            "fresh": age_days <= FRESH_THRESHOLD_DAYS,
            "is_stale": age_days > FRESH_THRESHOLD_DAYS,
            "freshness_status": status,
        }

    meta = {
        "version_id": raw_generated_at if isinstance(raw_generated_at, str) else None,
        "snapshot_origin": SNAPSHOT_ORIGIN,
        "generated_at": raw_generated_at if isinstance(raw_generated_at, str) else None,
        "record_count": _as_int(raw_meta.get("record_count")),
        "rejected_count": _as_int(raw_meta.get("rejected_count")),
        "source_status": _sanitise_source_status(raw_meta.get("source_status", [])),
        "confidence_counts": raw_meta.get("confidence_counts")
        if isinstance(raw_meta.get("confidence_counts"), dict)
        else None,
        **freshness,
    }

    _CACHE.update({"path": str(path), "metadata": meta, "loaded_at": now})
    return meta


def format_dataset_badge(meta):
    """Return (text, css_class_suffix) for the map badge.

    The text is in English to match the rest of the dashboard UI; the
    Portuguese methodology page lands in PR 2. The date format is
    day/month/year, as used in Angola.
    """
    if meta is None or meta.get("generated_at") is None or meta.get("age_days") is None:
        return "Dataset update date unavailable.", "unavailable"
    generated_at = _parse_generated_at(meta["generated_at"])
    if generated_at is None:
        return "Dataset update date unavailable.", "unavailable"
    label = generated_at.strftime("%d/%m/%Y")
    age_days = meta["age_days"]
    status = meta["freshness_status"]
    if status == "overdue":
        return (
            f"Updated on {label} ({age_days} days ago). Data is overdue.",
            "overdue",
        )
    if status == "stale":
        return (
            f"Updated on {label} ({age_days} days ago). Data is outdated.",
            "stale",
        )
    return f"Updated on {label} ({age_days} days ago).", "fresh"
