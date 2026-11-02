"""Tests for click-to-zoom map view: centre and zoom by selection."""

import unittest

import pandas as pd

from map_dashboard.data import map_view_for_selection


def _frame():
    return pd.DataFrame(
        [
            {"station": "Posto A", "latitude": -8.8, "longitude": 13.2},
            {"station": "Posto B", "latitude": -9.0, "longitude": 13.5},
        ]
    )


class MapViewTest(unittest.TestCase):
    def test_no_selection_centres_on_mean_zoomed_out(self):
        center, zoom = map_view_for_selection(_frame(), None)
        self.assertAlmostEqual(center["lat"], -8.9)
        self.assertAlmostEqual(center["lon"], 13.35)
        self.assertEqual(zoom, 5)

    def test_single_row_without_selection_zooms_closer(self):
        center, zoom = map_view_for_selection(_frame().iloc[[0]], None)
        self.assertAlmostEqual(center["lat"], -8.8)
        self.assertEqual(zoom, 11)

    def test_selected_station_centres_on_that_station_at_street_zoom(self):
        center, zoom = map_view_for_selection(_frame(), "Posto B")
        self.assertEqual(center, {"lat": -9.0, "lon": 13.5})
        self.assertEqual(zoom, 15)

    def test_unknown_selection_falls_back_to_mean(self):
        center, zoom = map_view_for_selection(_frame(), "Posto inexistente")
        self.assertAlmostEqual(center["lat"], -8.9)
        self.assertEqual(zoom, 5)


if __name__ == "__main__":
    unittest.main()
