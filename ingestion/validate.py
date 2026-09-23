"""Validation and deduplication helpers for station ingestion.

Quality gates (see docs/data-quality.md):
1. Operators are canonicalized against the verified registry
   (ingestion/operators.py) before anything else.
2. Records are validated (coordinates, required fields).
3. Near-duplicate records of the same physical station are merged.
4. Surviving records whose station name is still a raw OSM element id
   are rejected — only truly unnamed stations are dropped.
"""

import math
import re

from ingestion.operators import UNKNOWN_OPERATOR, canonicalize_record

ANGOLA_LATITUDE_RANGE = (-18.1, -4.3)
ANGOLA_LONGITUDE_RANGE = (11.4, 24.2)
BAD_TEXT_MARKERS = ("\u00c3", "\u00c2", "&#")
SOURCE_PRIORITY = {
    "operator_website": 0,
    "openstreetmap_operator": 1,
    "openstreetmap": 2,
    "legacy_snapshot": 3,
}
MERGE_RADIUS_METERS = 150
_OSM_ID_NAME_PATTERN = re.compile(r"^(node|way|relation)/\d+$")


def validate_station(record):
    reasons = []

    if not record.get("station"):
        reasons.append("missing station")
    if not record.get("operator"):
        reasons.append("missing operator")

    latitude = _as_float(record.get("latitude"))
    longitude = _as_float(record.get("longitude"))
    if latitude is None or longitude is None:
        reasons.append("missing or non-numeric coordinates")
    elif latitude == 0 and longitude == 0:
        reasons.append("null island coordinates")
    else:
        if not ANGOLA_LATITUDE_RANGE[0] <= latitude <= ANGOLA_LATITUDE_RANGE[1]:
            reasons.append("latitude outside Angola bounds")
        if not ANGOLA_LONGITUDE_RANGE[0] <= longitude <= ANGOLA_LONGITUDE_RANGE[1]:
            reasons.append("longitude outside Angola bounds")

    if _has_bad_text(record):
        reasons.append("possible encoding or html entity issue")

    clean_record = dict(record)
    clean_record["latitude"] = latitude
    clean_record["longitude"] = longitude
    return clean_record, reasons


def split_valid_records(records):
    clean_records = []
    rejected_records = []
    for record in records:
        canonical_record = canonicalize_record(record)
        clean_record, reasons = validate_station(canonical_record)
        if reasons:
            rejected_record = dict(clean_record)
            rejected_record["rejection_reasons"] = reasons
            rejected_records.append(rejected_record)
        else:
            clean_records.append(clean_record)
    merged_records = deduplicate_records(clean_records)
    final_clean, hygiene_rejected = _apply_name_hygiene(merged_records)
    return final_clean, rejected_records + hygiene_rejected


def deduplicate_records(records):
    """Merge records describing the same physical station.

    Precondition: record operators are already canonicalized
    (``split_valid_records`` does this; direct callers must too).

    Two records within ``MERGE_RADIUS_METERS`` are the same station
    unless both carry different verified (non-``Unknown``) operators —
    competing brands can sit across the street from each other and must
    never merge. The highest-priority record (see ``_record_priority``)
    survives and absorbs complementary fields from the merged ones.
    """
    ordered = sorted(records, key=_record_priority)
    survivors = []
    for record in ordered:
        candidate = dict(record)
        candidate["merged_sources"] = sorted(
            {source for source in [record.get("source_name")] if source}
        )
        target = next((s for s in survivors if _is_same_station(s, candidate)), None)
        if target is None:
            survivors.append(candidate)
        else:
            _merge_into(target, candidate)
    return survivors


def _is_same_station(a, b):
    try:
        distance = _haversine_m(
            float(a["latitude"]),
            float(a["longitude"]),
            float(b["latitude"]),
            float(b["longitude"]),
        )
    except (TypeError, ValueError):
        return False
    if distance > MERGE_RADIUS_METERS:
        return False
    operator_a = a.get("operator") or UNKNOWN_OPERATOR
    operator_b = b.get("operator") or UNKNOWN_OPERATOR
    if (
        operator_a != UNKNOWN_OPERATOR
        and operator_b != UNKNOWN_OPERATOR
        and operator_a != operator_b
    ):
        return False
    return True


def _merge_into(winner, loser):
    if _is_osm_id_name(winner.get("station")) and not _is_osm_id_name(
        loser.get("station")
    ):
        winner["station"] = loser["station"]
    winner_operator = winner.get("operator")
    loser_operator = loser.get("operator")
    if (not winner_operator or winner_operator == UNKNOWN_OPERATOR) and (
        loser_operator and loser_operator != UNKNOWN_OPERATOR
    ):
        winner["operator"] = loser_operator
    for field in ("address", "municipality", "province"):
        if not winner.get(field) and loser.get(field):
            winner[field] = loser[field]
    sources = set(winner.get("merged_sources") or [])
    sources.update(loser.get("merged_sources") or [])
    if loser.get("source_name"):
        sources.add(loser["source_name"])
    winner["merged_sources"] = sorted(source for source in sources if source)


def _apply_name_hygiene(records):
    clean_records = []
    rejected_records = []
    for record in records:
        if _is_osm_id_name(record.get("station")):
            rejected_record = dict(record)
            rejected_record["rejection_reasons"] = ["station name is an OSM element id"]
            rejected_records.append(rejected_record)
        else:
            clean_records.append(record)
    return clean_records, rejected_records


def _is_osm_id_name(name):
    return bool(_OSM_ID_NAME_PATTERN.match(str(name or "").strip()))


def _haversine_m(latitude_a, longitude_a, latitude_b, longitude_b):
    radius_m = 6371000
    phi_a = math.radians(latitude_a)
    phi_b = math.radians(latitude_b)
    delta_phi = math.radians(latitude_b - latitude_a)
    delta_lambda = math.radians(longitude_b - longitude_a)
    h = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi_a) * math.cos(phi_b) * math.sin(delta_lambda / 2) ** 2
    )
    return 2 * radius_m * math.asin(math.sqrt(h))


def _record_priority(record):
    is_stale = 1 if record.get("is_stale") else 0
    source_rank = SOURCE_PRIORITY.get(record.get("source_type"), 99)
    has_real_name = 0 if not _is_osm_id_name(record.get("station")) else 1
    has_address = 0 if record.get("address") else 1
    return is_stale, source_rank, has_real_name, has_address


def _as_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _has_bad_text(record):
    for value in record.values():
        if isinstance(value, str) and any(marker in value for marker in BAD_TEXT_MARKERS):
            return True
    return False
