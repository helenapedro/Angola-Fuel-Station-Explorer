"""Tests for the bundled data loading in data_fetch."""

import unittest
from pathlib import Path

import data_fetch


class BundledLoadTest(unittest.TestCase):
    def setUp(self):
        self._saved_cache = dict(data_fetch._CACHE)
        self._saved_clean_path = data_fetch.CLEAN_DATA_PATH
        data_fetch._CACHE.update(
            {"df": None, "fetched_at": 0.0, "error": None, "is_fallback": False}
        )

    def tearDown(self):
        data_fetch._CACHE.update(self._saved_cache)
        data_fetch.CLEAN_DATA_PATH = self._saved_clean_path

    def test_loads_bundled_snapshot(self):
        df, err = data_fetch.get_stations_df()
        self.assertIsNone(err)
        self.assertFalse(data_fetch.is_fallback_data())
        self.assertGreater(len(df), 0)
        for column in [
            "Operator",
            "Station",
            "Address",
            "Latitude",
            "Longitude",
            "Province",
            "Municipality",
            "Country",
        ]:
            self.assertIn(column, df.columns)

    def test_missing_snapshot_uses_legacy_fallback(self):
        data_fetch.CLEAN_DATA_PATH = Path("/nonexistent/stations_clean.json")
        df, err = data_fetch.get_stations_df()
        self.assertTrue(data_fetch.is_fallback_data())
        self.assertIsNotNone(err)
        self.assertGreater(len(df), 0)

    def test_no_requests_dependency(self):
        # The legacy HTTP fetch is gone; data_fetch must not need requests.
        self.assertFalse(hasattr(data_fetch, "requests"))
        self.assertFalse(hasattr(data_fetch, "API_URL"))


if __name__ == "__main__":
    unittest.main()
