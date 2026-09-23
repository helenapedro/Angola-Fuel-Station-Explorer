"""Tests for the shared station normalization module.

Covers alias resolution, text/float cleaning, stable ID determinism,
the coordinate-validity definition, and the API data-access integration.
"""

import time
import unittest

import pandas as pd

import data_fetch
import station_data
from api import db


def _fallback_style_df() -> pd.DataFrame:
    # Capitalized columns, as produced by data_fetch._load_fallback_df().
    return pd.DataFrame(
        [
            {
                "Operator": "  Pumangol ",
                "Station": "Viana Km30",
                "Address": "Via Expresso",
                "Municipality": "Viana",
                "Province": "Luanda",
                "Country": "Angola",
                "Latitude": "-8.964739",
                "Longitude": "13.470033",
            },
            {
                "Operator": "Sonangol",
                "Station": "Cazenga",
                "Address": "",
                "Municipality": "Cazenga",
                "Province": "Luanda",
                "Country": "Angola",
                "Latitude": 0,
                "Longitude": 0,
            },
        ]
    )


class NormalizeTest(unittest.TestCase):
    def test_alias_resolution_and_cleaning(self):
        df = station_data.normalize_stations_df(_fallback_style_df())
        self.assertEqual(list(df.columns), ["id", *station_data.CANONICAL_COLUMNS])
        self.assertEqual(df.loc[0, "operator"], "Pumangol")  # stripped
        self.assertEqual(df.loc[0, "latitude"], -8.964739)  # coerced to float
        self.assertIsNone(df.loc[1, "address"])  # empty string -> None

    def test_alternate_aliases(self):
        df = station_data.normalize_stations_df(
            pd.DataFrame(
                [{"name": "X", "state": "Benguela", "lat": "-12.5", "lng": "13.4"}]
            )
        )
        self.assertEqual(df.loc[0, "station"], "X")
        self.assertEqual(df.loc[0, "province"], "Benguela")
        self.assertEqual(df.loc[0, "latitude"], -12.5)
        self.assertEqual(df.loc[0, "longitude"], 13.4)

    def test_invalid_floats_become_none(self):
        df = station_data.normalize_stations_df(
            pd.DataFrame([{"station": "X", "latitude": "not-a-number", "longitude": float("nan")}])
        )
        self.assertIsNone(df.loc[0, "latitude"])
        self.assertIsNone(df.loc[0, "longitude"])

    def test_missing_columns_become_none(self):
        df = station_data.normalize_stations_df(pd.DataFrame([{"station": "X"}]))
        self.assertIsNone(df.loc[0, "operator"])
        self.assertIsNone(df.loc[0, "latitude"])

    def test_empty_frame(self):
        df = station_data.normalize_stations_df(pd.DataFrame())
        self.assertTrue(df.empty)
        self.assertEqual(list(df.columns), ["id", *station_data.CANONICAL_COLUMNS])

    def test_does_not_drop_rows(self):
        # Validity filtering is a view-level concern; normalization keeps
        # every row so consumers can decide.
        df = station_data.normalize_stations_df(_fallback_style_df())
        self.assertEqual(len(df), 2)


class StableIdTest(unittest.TestCase):
    def test_deterministic_across_runs(self):
        df = _fallback_style_df()
        first = station_data.normalize_stations_df(df)["id"].tolist()
        second = station_data.normalize_stations_df(df)["id"].tolist()
        self.assertEqual(first, second)

    def test_distinct_stations_get_distinct_ids(self):
        df = station_data.normalize_stations_df(_fallback_style_df())
        self.assertEqual(len(set(df["id"])), 2)

    def test_id_is_positive_int(self):
        df = station_data.normalize_stations_df(_fallback_style_df())
        for value in df["id"]:
            self.assertIsInstance(value, int)
            self.assertGreater(value, 0)

    def test_id_insensitive_to_whitespace_and_case(self):
        row = {"operator": "Pumangol", "station": "Viana Km30", "latitude": -8.9, "longitude": 13.4}
        noisy = dict(row, operator="  pumangol ", station="viana km30")
        self.assertEqual(
            station_data.stable_station_id(**row), station_data.stable_station_id(**noisy)
        )


class ValidCoordinatesMaskTest(unittest.TestCase):
    def test_mask(self):
        df = pd.DataFrame(
            {
                "latitude": [-8.9, 0, -40.0, None, -8.9],
                "longitude": [13.4, 0, 13.4, 13.4, None],
            }
        )
        mask = station_data.valid_coordinates_mask(df).tolist()
        # valid, null island, outside Angola, missing lat, missing lon
        self.assertEqual(mask, [True, False, False, False, False])


class DbIntegrationTest(unittest.TestCase):
    def setUp(self):
        self._saved_cache = dict(data_fetch._CACHE)

    def tearDown(self):
        data_fetch._CACHE.update(self._saved_cache)

    def _prime_cache(self, df, is_fallback):
        data_fetch._CACHE.update(
            {"df": df, "fetched_at": time.time(), "error": None, "is_fallback": is_fallback}
        )

    def test_load_stations_df_live(self):
        self._prime_cache(_fallback_style_df(), is_fallback=False)
        df, source = db.load_stations_df()
        self.assertEqual(source, "live")
        self.assertEqual(list(df.columns), ["id", *station_data.CANONICAL_COLUMNS])
        self.assertEqual(df.loc[0, "operator"], "Pumangol")

    def test_load_stations_df_fallback_label(self):
        self._prime_cache(_fallback_style_df(), is_fallback=True)
        _df, source = db.load_stations_df()
        self.assertEqual(source, "fallback")


if __name__ == "__main__":
    unittest.main()
