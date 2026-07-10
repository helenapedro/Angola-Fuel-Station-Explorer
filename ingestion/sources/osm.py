"""OpenStreetMap fuel-station source using Overpass API."""

import requests

from ingestion.normalize import normalize_osm_element, utc_now_iso

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
REQUEST_TIMEOUT_SECONDS = 30
USER_AGENT = "gasmapdash-station-ingestion/1.0"

ANGOLA_FUEL_STATIONS_QUERY = """
[out:json][timeout:60];
area["ISO3166-1"="AO"][admin_level=2]->.angola;
(
  node["amenity"="fuel"](area.angola);
  way["amenity"="fuel"](area.angola);
  relation["amenity"="fuel"](area.angola);
);
out center tags;
"""


def fetch_osm_stations(overpass_url=OVERPASS_URL):
    response = requests.post(
        overpass_url,
        data={"data": ANGOLA_FUEL_STATIONS_QUERY},
        headers={"User-Agent": USER_AGENT},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    payload = response.json()
    scraped_at = utc_now_iso()
    return [normalize_osm_element(element, scraped_at=scraped_at) for element in payload.get("elements", [])]
