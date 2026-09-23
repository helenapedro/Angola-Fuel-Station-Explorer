"""Tests for the offline geocoding backfill (ingestion/geocode.py).

All offline: plus codes are computed locally, no network, no mocks.
"""

import unittest

from ingestion.geocode import (
    ADDRESS_SOURCE_PLUS_CODE,
    backfill_geocode,
    station_plus_code,
)
from ingestion.validate import deduplicate_records


def _record(**overrides):
    record = {
        "station": "Posto Teste",
        "operator": "Sonangol",
        "latitude": -7.7602146,
        "longitude": 15.2694335,
        "address": "",
        "municipality": "",
        "province": "",
    }
    record.update(overrides)
    return record


class PlusCodeTest(unittest.TestCase):
    def test_helena_example_matches_google(self):
        # Helena verified on Google Maps: -7.7602146, 15.2694335 is
        # "67Q9+WQ7 Negage, Angola" — the bare full code below.
        self.assertEqual(
            station_plus_code(-7.7602146, 15.2694335), "6F4Q67Q9+WQ7"
        )

    def test_plus_code_is_deterministic(self):
        self.assertEqual(
            station_plus_code(-8.8383, 13.2344),
            station_plus_code(-8.8383, 13.2344),
        )

    def test_plus_code_format(self):
        code = station_plus_code(-8.8383, 13.2344)
        self.assertIn("+", code)
        self.assertEqual(len(code.replace("+", "")), 11)


class BackfillGeocodeTest(unittest.TestCase):
    def test_never_overwrites_existing_address(self):
        record = _record(address="Rua X")
        filled, stats = backfill_geocode([record])
        self.assertEqual(filled[0]["address"], "Rua X")
        self.assertNotIn("address_source", filled[0])
        self.assertEqual(stats, {"address_filled": 0})

    def test_fills_empty_address_with_full_plus_code(self):
        record = _record()
        filled, stats = backfill_geocode([record])
        self.assertEqual(filled[0]["address"], "6F4Q67Q9+WQ7")
        self.assertEqual(filled[0]["address_source"], ADDRESS_SOURCE_PLUS_CODE)
        self.assertEqual(stats["address_filled"], 1)

    def test_whitespace_address_counts_as_empty(self):
        record = _record(address="   ")
        filled, stats = backfill_geocode([record])
        self.assertEqual(filled[0]["address"], "6F4Q67Q9+WQ7")
        self.assertEqual(stats["address_filled"], 1)

    def test_invalid_coordinates_are_skipped(self):
        for bad in (
            {"latitude": None, "longitude": 15.0},
            {"latitude": "abc", "longitude": 15.0},
            {"latitude": 0, "longitude": 0},
        ):
            filled, stats = backfill_geocode([_record(**bad)])
            self.assertEqual(filled[0]["address"], "")
            self.assertNotIn("address_source", filled[0])
        self.assertEqual(stats["address_filled"], 0)

    def test_leaves_municipality_and_province_alone(self):
        # Offline backfill is address-only; the municipality->province
        # table (ingestion/provinces.py) handles provinces separately.
        record = _record(municipality="Luanda", province="Luanda")
        filled, _ = backfill_geocode([record])
        self.assertEqual(filled[0]["municipality"], "Luanda")
        self.assertEqual(filled[0]["province"], "Luanda")

    def test_does_not_mutate_input(self):
        record = _record()
        snapshot = dict(record)
        backfill_geocode([record])
        self.assertEqual(record, snapshot)


class MergePrefersRealAddressTest(unittest.TestCase):
    def test_real_address_beats_plus_code_placeholder(self):
        winner = _record(
            latitude=-7.7602146,
            longitude=15.2694335,
            address="6F4Q67Q9+WQ7",
            address_source=ADDRESS_SOURCE_PLUS_CODE,
            source_type="operator_website",
            source_name="Sonangol",
        )
        loser = _record(
            latitude=-7.7602147,
            longitude=15.2694336,
            address="Rua Principal 123",
            source_type="openstreetmap",
            source_name="OSM",
        )
        merged = deduplicate_records([winner, loser])
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["address"], "Rua Principal 123")
        self.assertNotIn("address_source", merged[0])

    def test_plus_code_survives_when_no_real_address(self):
        winner = _record(
            address="6F4Q67Q9+WQ7",
            address_source=ADDRESS_SOURCE_PLUS_CODE,
            source_type="operator_website",
            source_name="Sonangol",
        )
        loser = _record(
            latitude=-7.7602147,
            longitude=15.2694336,
            source_type="openstreetmap",
            source_name="OSM",
        )
        merged = deduplicate_records([winner, loser])
        self.assertEqual(merged[0]["address"], "6F4Q67Q9+WQ7")
        self.assertEqual(merged[0]["address_source"], ADDRESS_SOURCE_PLUS_CODE)


if __name__ == "__main__":
    unittest.main()
