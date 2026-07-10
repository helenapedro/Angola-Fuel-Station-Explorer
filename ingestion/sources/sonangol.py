"""Sonangol station source backed by OpenStreetMap operator/brand tags.

The public Sonangol website exposes distribution/commercialization content, but
no station-listing endpoint has been identified yet. This adapter gives
Sonangol-specific source health while using OSM as the refreshable source.
"""

from ingestion.normalize import normalize_osm_element, utc_now_iso

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
REQUEST_TIMEOUT_SECONDS = 30
USER_AGENT = "gasmapdash-station-ingestion/1.0"
SOURCE_NAME = "SonangolOpenStreetMap"

SONANGOL_FUEL_STATIONS_QUERY = """
[out:json][timeout:60];
area["ISO3166-1"="AO"][admin_level=2]->.angola;
(
  node["amenity"="fuel"]["brand"~"Sonangol",i](area.angola);
  way["amenity"="fuel"]["brand"~"Sonangol",i](area.angola);
  relation["amenity"="fuel"]["brand"~"Sonangol",i](area.angola);
  node["amenity"="fuel"]["operator"~"Sonangol",i](area.angola);
  way["amenity"="fuel"]["operator"~"Sonangol",i](area.angola);
  relation["amenity"="fuel"]["operator"~"Sonangol",i](area.angola);
);
out center tags;
"""


def fetch_sonangol_stations(overpass_url=OVERPASS_URL):
    import requests

    response = requests.post(
        overpass_url,
        data={"data": SONANGOL_FUEL_STATIONS_QUERY},
        headers={"User-Agent": USER_AGENT},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    payload = response.json()
    return normalize_sonangol_payload(payload)


def normalize_sonangol_payload(payload, scraped_at=None):
    scraped_at = scraped_at or utc_now_iso()
    return [
        normalize_sonangol_osm_element(element, scraped_at=scraped_at)
        for element in payload.get("elements", [])
        if is_sonangol_element(element)
    ]


def normalize_sonangol_osm_element(element, scraped_at=None):
    record = normalize_osm_element(element, scraped_at=scraped_at)
    record["operator"] = "Sonangol"
    record["source_type"] = "openstreetmap_operator"
    record["source_name"] = SOURCE_NAME
    record["source_url"] = "https://www.openstreetmap.org"
    return record


def is_sonangol_element(element):
    tags = element.get("tags") or {}
    values = [tags.get("brand", ""), tags.get("operator", ""), tags.get("name", "")]
    return any("sonangol" in str(value).casefold() for value in values)
