"""Tests for click-to-zoom map view: centre and zoom by selection, and cluster clicks."""

import unittest
from pathlib import Path

import pandas as pd

from map_dashboard.data import is_cluster_click, map_view_for_selection


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


class ClusterClickTest(unittest.TestCase):
    def test_cluster_click_has_no_customdata(self):
        self.assertTrue(is_cluster_click({"points": [{"lat": -8.8, "lon": 13.2}]}))

    def test_station_click_has_customdata(self):
        self.assertFalse(is_cluster_click({"points": [{"customdata": ["Posto A", "Sonangol"]}]}))

    def test_no_click_data_is_not_a_cluster_click(self):
        self.assertFalse(is_cluster_click(None))
        self.assertFalse(is_cluster_click({"points": []}))


class ClusterConfigTest(unittest.TestCase):
    def test_map_figure_enables_clustering(self):
        # Source-text check: presentation.py imports Plotly and Dash,
        # which CI does not install, like tests/test_navigation.py.
        source = (Path(__file__).resolve().parents[1] / "map_dashboard" / "presentation.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('"enabled": True', source)
        self.assertIn('"maxzoom": 14', source)
        self.assertIn('"step": [5, 25]', source)


if __name__ == "__main__":
    unittest.main()
