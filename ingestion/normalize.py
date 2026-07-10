"""Normalize station records from source-specific shapes into one schema."""

from datetime import datetime, timezone
from html import unescape


def utc_now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def clean_text(value):
    if value is None:
        return ""
    return " ".join(unescape(str(value)).replace("\xa0", " ").split()).strip()


def split_city(city):
    parts = [clean_text(part) for part in str(city or "").split("-") if clean_text(part)]
    if len(parts) >= 2:
        return parts[-1], parts[0]
    if parts:
        return parts[0], parts[0]
    return "", ""


def normalize_legacy_pumangol(record, scraped_at=None):
    municipality, parsed_province = split_city(record.get("city"))
    return {
        "operator": "Pumangol",
        "station": clean_text(record.get("name")),
        "address": clean_text(record.get("address")),
        "province": clean_text(record.get("state")) or parsed_province,
        "municipality": municipality,
        "country": clean_text(record.get("country")) or "Angola",
        "latitude": record.get("latitude"),
        "longitude": record.get("longitude"),
        "source_type": "operator_website",
        "source_name": "Pumangol",
        "source_url": "https://www.pumangol.co.ao/pt/institucional/mapa-de-postos-de-abastecimento",
        "source_id": clean_text(record.get("name")),
        "scraped_at": scraped_at or utc_now_iso(),
    }


def normalize_osm_element(element, scraped_at=None):
    tags = element.get("tags") or {}
    center = element.get("center") or {}
    latitude = element.get("lat", center.get("lat"))
    longitude = element.get("lon", center.get("lon"))
    source_id = f'{element.get("type")}/{element.get("id")}'

    return {
        "operator": clean_text(tags.get("operator") or tags.get("brand") or "Unknown"),
        "station": clean_text(tags.get("name") or tags.get("brand") or tags.get("operator") or source_id),
        "address": clean_text(_format_osm_address(tags)),
        "province": clean_text(tags.get("addr:province") or tags.get("is_in:province")),
        "municipality": clean_text(tags.get("addr:city") or tags.get("addr:municipality")),
        "country": "Angola",
        "latitude": latitude,
        "longitude": longitude,
        "source_type": "openstreetmap",
        "source_name": "OpenStreetMap",
        "source_url": "https://www.openstreetmap.org",
        "source_id": source_id,
        "scraped_at": scraped_at or utc_now_iso(),
    }


def _format_osm_address(tags):
    address_parts = [
        tags.get("addr:street"),
        tags.get("addr:housenumber"),
        tags.get("addr:suburb"),
        tags.get("addr:city"),
    ]
    return ", ".join(clean_text(part) for part in address_parts if clean_text(part))
