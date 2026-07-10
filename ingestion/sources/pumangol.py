"""Pumangol website station source."""

import json
import re

import requests

from ingestion.normalize import normalize_legacy_pumangol, utc_now_iso

PUMANGOL_STATIONS_URL = "https://www.pumangol.co.ao/pt/institucional/mapa-de-postos-de-abastecimento"
REQUEST_TIMEOUT_SECONDS = 20
USER_AGENT = "gasmapdash-station-ingestion/1.0"


def fetch_pumangol_stations(url=PUMANGOL_STATIONS_URL):
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    stores_payload = extract_stores_payload(response.text)
    scraped_at = utc_now_iso()

    records = []
    for feature in stores_payload.get("features", []):
        coordinates = feature.get("geometry", {}).get("coordinates", [])
        properties = feature.get("properties", {})
        legacy_record = {
            "name": properties.get("title"),
            "address": properties.get("address"),
            "city": properties.get("city"),
            "state": properties.get("state"),
            "country": properties.get("country"),
            "latitude": coordinates[1] if len(coordinates) > 1 else None,
            "longitude": coordinates[0] if coordinates else None,
        }
        records.append(normalize_legacy_pumangol(legacy_record, scraped_at=scraped_at))
    return records


def extract_stores_payload(html):
    match = re.search(r"const\s+stores\s*=\s*(\{.*?\});", html, re.DOTALL)
    if not match:
        raise ValueError("Pumangol stores payload not found")

    stores_data = re.sub(r",\s*([}\]])", r"\1", match.group(1))
    stores_data = stores_data.replace("'", '"')
    return json.loads(stores_data)
