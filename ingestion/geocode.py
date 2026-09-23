"""Geocoding backfill: addresses from coordinates, fully offline.

Every station has coordinates but many lack ``address``. This module
fills the gap with plus codes (open location codes) computed locally —
pure math, no network, no API keys, no rate limits, fully
deterministic. The bare full code (e.g. ``6F4Q67Q9+WQ7``) resolves in
Google Maps, so no locality suffix is needed.

Design decision (2026-09-23, at Helena's direction): this used to
reverse-geocode municipality/province via Nominatim, but ~144
sequential network requests trip the sandbox network approval gate, so
the online path was dropped entirely. Municipality/province backfill
now relies solely on the explicit municipality->province table
(``ingestion/provinces.py``), which runs before this module. A spatial
join against offline admin boundaries (GADM/geoBoundaries) was
considered and rejected: those datasets predate Angola's 2024 reform
(18 provinces) and would mislabel post-reform areas. See
``docs/geocoding-backfill.md``.

Rules: fill empty addresses only, never overwrite; records keep
``address_source="plus_code"`` so a real street address arriving later
wins the dedup merge (see ``ingestion/validate.py``).
"""

from openlocationcode import openlocationcode as olc

GEOCODE_BACKFILL_VERSION = 2
ADDRESS_SOURCE_PLUS_CODE = "plus_code"
PLUS_CODE_LENGTH = 11  # ~3 m precision


def station_plus_code(latitude, longitude):
    """Full plus code for the coordinates, e.g. ``6F4Q67Q9+WQ7``."""
    return olc.encode(float(latitude), float(longitude), PLUS_CODE_LENGTH)


def _valid_coords(record):
    try:
        latitude = float(record.get("latitude"))
        longitude = float(record.get("longitude"))
    except (TypeError, ValueError):
        return None
    if latitude == 0 and longitude == 0:
        return None
    return latitude, longitude


def backfill_geocode(records):
    """Fill empty addresses with locally computed plus codes.

    Returns ``(records, stats)`` with copies — input records are not
    mutated. ``stats`` is ``{"address_filled": n}`` for the run
    metadata.
    """
    filled_records = []
    stats = {"address_filled": 0}
    for record in records:
        filled = dict(record)
        coords = _valid_coords(filled)
        if coords is None:
            filled_records.append(filled)
            continue
        if not (filled.get("address") or "").strip():
            filled["address"] = station_plus_code(*coords)
            filled["address_source"] = ADDRESS_SOURCE_PLUS_CODE
            stats["address_filled"] += 1
        filled_records.append(filled)
    return filled_records, stats
