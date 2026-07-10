"""Validation and deduplication helpers for station ingestion."""

ANGOLA_LATITUDE_RANGE = (-18.1, -4.3)
ANGOLA_LONGITUDE_RANGE = (11.4, 24.2)
BAD_TEXT_MARKERS = ("\u00c3", "\u00c2", "&#")
SOURCE_PRIORITY = {
    "operator_website": 0,
    "openstreetmap_operator": 1,
    "openstreetmap": 2,
    "legacy_snapshot": 3,
}


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
        clean_record, reasons = validate_station(record)
        if reasons:
            rejected_record = dict(clean_record)
            rejected_record["rejection_reasons"] = reasons
            rejected_records.append(rejected_record)
        else:
            clean_records.append(clean_record)
    return deduplicate_records(clean_records), rejected_records


def deduplicate_records(records):
    seen = set()
    deduped = []
    for record in sorted(records, key=_record_priority):
        key = _dedupe_key(record)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(record)
    return deduped


def _dedupe_key(record):
    latitude = round(float(record["latitude"]), 4)
    longitude = round(float(record["longitude"]), 4)
    return (
        _normalize_key(record.get("operator")),
        _normalize_key(record.get("station")),
        latitude,
        longitude,
    )


def _record_priority(record):
    is_stale = 1 if record.get("is_stale") else 0
    source_rank = SOURCE_PRIORITY.get(record.get("source_type"), 99)
    has_address = 0 if record.get("address") else 1
    return is_stale, source_rank, has_address


def _normalize_key(value):
    return " ".join(str(value or "").casefold().split())


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
