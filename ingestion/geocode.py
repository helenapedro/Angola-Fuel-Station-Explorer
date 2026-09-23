"""Geocoding backfill: addresses, municipalities, provinces from coordinates.

Every station has coordinates but many lack ``address``/``municipality``/
``province``. This module fills the gaps without guessing:

- ``address``: computed offline as a plus code (open location code) —
  full 11-char code, or the compound ``"<short> <locality>, Angola"``
  form when the municipality is known. No API, no cost, always works.
- ``municipality``/``province``: OpenStreetMap Nominatim reverse
  geocoding, cached in ``data/geocode_cache.json`` so weekly refreshes
  are incremental. Any failure leaves the field empty; the pipeline
  never fails because geocoding failed.

Rules (see docs/geocoding-backfill.md): fill empty fields only, never
overwrite; the curated municipality->province table
(``ingestion/provinces.py``) runs before this and outranks it.
"""

import json
import time
from pathlib import Path

import requests
from openlocationcode import openlocationcode as olc

GEOCODE_BACKFILL_VERSION = 1
ADDRESS_SOURCE_PLUS_CODE = "plus_code"
PLUS_CODE_LENGTH = 11  # ~3 m precision
NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"
NOMINATIM_THROTTLE_SECONDS = 1.1
NOMINATIM_TIMEOUT_SECONDS = 20
USER_AGENT = (
    "AngolaFuelStationExplorer/1.0 "
    "(https://github.com/helenapedro/Angola-Fuel-Station-Explorer; "
    "station data-quality pipeline)"
)

# Nominatim (post-2024-reform, Portuguese spellings) -> dataset spellings.
# Provinces unknown to this map pass through cleaned but unmapped —
# e.g. "Icolo e Bengo" is a real new province, not a spelling variant.
_PROVINCE_NORMALIZATION = {
    "uíge": "Uige",
    "malanje": "Malange",
    "cuando cubango": "Kuando Kubango",
    "bié": "Bie",
    "huíla": "Huila",
    "cuanza norte": "Kwanza Norte",
    "cuanza sul": "Kwanza Sul",
    "ícolo e bengo": "Icolo e Bengo",
}
_PROVINCE_SUFFIXES = (" province", " província", " provincia")

# Nominatim address keys in municipality-priority order. suburb/road are
# deliberately excluded: bairro level, not municipality.
_MUNICIPALITY_KEYS = ("municipality", "county", "city", "town", "village")
_MUNICIPALITY_PREFIXES = (
    "município de ",
    "município do ",
    "município da ",
    "município dos ",
    "município das ",
)


def station_plus_code(latitude, longitude):
    """Full plus code for the coordinates, e.g. ``6F4Q67Q9+WQ7``."""
    return olc.encode(float(latitude), float(longitude), PLUS_CODE_LENGTH)


def compound_address(latitude, longitude, locality):
    """Human-friendly address for stations without a street address.

    ``"67Q9+WQ7 Negage, Angola"`` when the municipality is known (the
    first 4 code characters are recoverable from the locality name,
    exactly Google's compound format); otherwise the full plus code.
    """
    full = station_plus_code(latitude, longitude)
    locality = (locality or "").strip()
    if locality:
        return f"{full[4:]} {locality}, Angola"
    return full


def clean_province(raw):
    """Normalize a Nominatim ``state`` value to dataset spelling."""
    name = " ".join(str(raw or "").split())
    lowered = name.casefold()
    for suffix in _PROVINCE_SUFFIXES:
        if lowered.endswith(suffix):
            name = name[: -len(suffix)].strip()
            lowered = name.casefold()
            break
    return _PROVINCE_NORMALIZATION.get(lowered, name)


def clean_municipality(raw):
    """Strip ``Município de/do/da/...`` prefixes from Nominatim values."""
    name = " ".join(str(raw or "").split())
    lowered = name.casefold()
    for prefix in _MUNICIPALITY_PREFIXES:
        if lowered.startswith(prefix):
            return name[len(prefix):].strip()
    return name


class NominatimClient:
    """Throttled, cached Nominatim reverse geocoder.

    ``reverse()`` returns ``{"province": ..., "municipality": ...}``
    (either may be ``None``) or ``None`` when the lookup fails — the
    caller treats that as "leave the field empty". Results are cached
    on disk keyed by rounded coordinates.
    """

    def __init__(self, cache_path=None, throttle_seconds=NOMINATIM_THROTTLE_SECONDS):
        self.cache_path = Path(cache_path) if cache_path else None
        self.throttle_seconds = throttle_seconds
        self._cache = self._load_cache()
        self._last_request_at = 0.0

    def reverse(self, latitude, longitude):
        try:
            lat = float(latitude)
            lng = float(longitude)
        except (TypeError, ValueError):
            return None
        key = f"{lat:.4f},{lng:.4f}"
        if key in self._cache:
            return self._cache[key]
        result = self._fetch(lat, lng)
        self._cache[key] = result
        self._save_cache()
        return result

    def _fetch(self, latitude, longitude):
        wait = self.throttle_seconds - (time.monotonic() - self._last_request_at)
        if wait > 0:
            time.sleep(wait)
        try:
            response = requests.get(
                NOMINATIM_URL,
                params={
                    "lat": latitude,
                    "lon": longitude,
                    "format": "json",
                    "addressdetails": 1,
                    "zoom": 14,
                },
                headers={"User-Agent": USER_AGENT},
                timeout=NOMINATIM_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            address = response.json().get("address") or {}
        except Exception:
            return None
        finally:
            self._last_request_at = time.monotonic()
        province = clean_province(address.get("state")) or None
        municipality = next(
            (
                cleaned
                for raw in (address.get(key) for key in _MUNICIPALITY_KEYS)
                for cleaned in [clean_municipality(raw)]
                if cleaned
            ),
            None,
        )
        if not province and not municipality:
            return None
        return {"province": province, "municipality": municipality}

    def _load_cache(self):
        if self.cache_path and self.cache_path.exists():
            try:
                return json.loads(self.cache_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return {}
        return {}

    def _save_cache(self):
        if self.cache_path:
            try:
                self.cache_path.parent.mkdir(parents=True, exist_ok=True)
                self.cache_path.write_text(
                    json.dumps(self._cache, ensure_ascii=False, indent=2, sort_keys=True),
                    encoding="utf-8",
                )
            except OSError:
                pass


def _valid_coords(record):
    try:
        latitude = float(record.get("latitude"))
        longitude = float(record.get("longitude"))
    except (TypeError, ValueError):
        return None
    if latitude == 0 and longitude == 0:
        return None
    return latitude, longitude


def backfill_geocode(records, client=None):
    """Fill empty address/municipality/province fields from coordinates.

    Runs after ``split_valid_records`` (dedup first = fewer API calls).
    ``client=None`` means offline mode: plus-code addresses still fill,
    Nominatim lookups are skipped. Returns ``(records, stats)`` with
    copies — input records are not mutated.
    """
    filled_records = []
    stats = {"address_filled": 0, "municipality_filled": 0, "province_filled": 0}
    for record in records:
        filled = dict(record)
        coords = _valid_coords(filled)
        if coords is None:
            filled_records.append(filled)
            continue
        latitude, longitude = coords

        lookup = None
        if client is not None and (
            not filled.get("municipality") or not filled.get("province")
        ):
            lookup = client.reverse(latitude, longitude) or {}

        if not filled.get("municipality"):
            municipality = (lookup or {}).get("municipality")
            if municipality:
                filled["municipality"] = municipality
                filled["municipality_inferred"] = True
                stats["municipality_filled"] += 1
            else:
                filled.setdefault("municipality_inferred", False)
        else:
            # Preserve a previous run's flag: stale records re-enter the
            # pipeline and must keep their inferred provenance.
            filled.setdefault("municipality_inferred", False)

        if not filled.get("province"):
            province = (lookup or {}).get("province")
            if province:
                filled["province"] = province
                filled["province_inferred"] = True
                stats["province_filled"] += 1
            else:
                filled.setdefault("province_inferred", False)
        else:
            filled.setdefault("province_inferred", False)

        if not (filled.get("address") or "").strip():
            filled["address"] = compound_address(
                latitude, longitude, filled.get("municipality")
            )
            filled["address_source"] = ADDRESS_SOURCE_PLUS_CODE
            stats["address_filled"] += 1

        filled_records.append(filled)
    return filled_records, stats
