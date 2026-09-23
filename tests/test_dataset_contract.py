"""Contract tests over the committed dataset snapshots.

Unit tests cover the ingestion functions; these tests guard the artifact
itself: whatever the pipeline produced and was committed must satisfy the
dataset's public contract. They run offline (no network) in CI on every PR,
so a silent data regression — a broken alias table, a lost dedupe step, a
bad regeneration — fails the build instead of reaching production.
"""

import json
import unittest
from pathlib import Path

from ingestion.operators import CANONICAL_OPERATORS, UNKNOWN_OPERATOR
from ingestion.validate import (
    ANGOLA_LATITUDE_RANGE,
    ANGOLA_LONGITUDE_RANGE,
    _OSM_ID_NAME_PATTERN,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
CLEAN_PATH = REPO_ROOT / "data" / "stations_clean.json"
REJECTED_PATH = REPO_ROOT / "data" / "stations_rejected.json"

# Guardrail: the Unknown share must stay a small, honest bucket. If a
# registry or pipeline change pushes it above this, something regressed.
MAX_UNKNOWN_FRACTION = 0.20


class DatasetContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.clean = json.loads(CLEAN_PATH.read_text(encoding="utf-8"))
        cls.rejected = json.loads(REJECTED_PATH.read_text(encoding="utf-8"))
        cls.stations = cls.clean["stations"]

    def test_operators_within_registry_or_unknown(self):
        allowed = set(CANONICAL_OPERATORS) | {UNKNOWN_OPERATOR}
        for station in self.stations:
            self.assertIn(
                station.get("operator"), allowed, station.get("source_id")
            )

    def test_no_osm_id_station_names_served(self):
        bad = [
            station.get("source_id")
            for station in self.stations
            if _OSM_ID_NAME_PATTERN.match(station.get("station") or "")
        ]
        self.assertEqual(bad, [])

    def test_unknown_fraction_below_threshold(self):
        unknown = sum(
            1 for s in self.stations if s.get("operator") == UNKNOWN_OPERATOR
        )
        fraction = unknown / len(self.stations)
        self.assertLess(
            fraction,
            MAX_UNKNOWN_FRACTION,
            f"{unknown}/{len(self.stations)} stations are Unknown",
        )

    def test_clean_coordinates_inside_angola(self):
        lat_min, lat_max = ANGOLA_LATITUDE_RANGE
        lon_min, lon_max = ANGOLA_LONGITUDE_RANGE
        for station in self.stations:
            lat, lon = station.get("latitude"), station.get("longitude")
            self.assertTrue(
                lat_min <= lat <= lat_max and lon_min <= lon <= lon_max,
                f"{station.get('source_id')}: ({lat}, {lon})",
            )

    def test_clean_records_carry_provenance(self):
        for station in self.stations:
            self.assertTrue(
                station.get("merged_sources"), station.get("source_id")
            )

    def test_rejected_records_carry_reasons(self):
        self.assertTrue(self.rejected["stations"])
        for station in self.rejected["stations"]:
            self.assertTrue(
                station.get("rejection_reasons"), station.get("source_id")
            )

    def test_stations_with_coordinates_have_address(self):
        # Plus codes are computed offline from coordinates, so every
        # clean station must have a navigable address — a silent
        # regression in the geocode backfill fails the build here.
        bad = [
            station.get("source_id")
            for station in self.stations
            if not (station.get("address") or "").strip()
        ]
        self.assertEqual(bad, [])


if __name__ == "__main__":
    unittest.main()
