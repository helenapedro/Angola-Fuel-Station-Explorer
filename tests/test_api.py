"""Tests for the FastAPI stations layer.

The dataset dependency is overridden with a small fixed dataset so the
tests are deterministic and never touch the network.
"""

import unittest

import pandas as pd
from fastapi.testclient import TestClient

from api.deps import get_station_data
from api.main import app


def _sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "id": 1,
                "operator": "Sonangol",
                "station": "Sonangol Cazenga",
                "address": "Rua X",
                "municipality": "Cazenga",
                "province": "Luanda",
                "country": "Angola",
                "latitude": -8.8,
                "longitude": 13.2,
            },
            {
                "id": 2,
                "operator": "Pumangol",
                "station": "Pumangol Viana",
                "address": "Rua Y",
                "municipality": "Viana",
                "province": "Luanda",
                "country": "Angola",
                "latitude": -8.9,
                "longitude": 13.3,
            },
            {
                "id": 3,
                "operator": "Sonangol",
                "station": "Sonangol Benguela",
                "address": "Rua Z",
                "municipality": "Benguela",
                "province": "Benguela",
                "country": "Angola",
                "latitude": -12.5,
                "longitude": 13.4,
            },
        ]
    )


class StationApiTest(unittest.TestCase):
    def setUp(self):
        app.dependency_overrides[get_station_data] = lambda: (_sample_df(), "live")
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_health_reports_ok(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["stations"], 3)
        self.assertEqual(body["source"], "live")

    def test_api_index_lists_routes(self):
        response = self.client.get("/api/v1")
        self.assertEqual(response.status_code, 200)
        endpoints = response.json()["endpoints"]
        self.assertIn("GET /health", endpoints)
        self.assertIn("GET /api/v1/stations", endpoints)

    def test_list_stations_paginates(self):
        response = self.client.get("/api/v1/stations", params={"page": 2, "page_size": 2})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["page"], 2)
        self.assertEqual(body["page_size"], 2)
        self.assertEqual(body["total"], 3)
        self.assertEqual(body["total_pages"], 2)
        self.assertEqual(len(body["items"]), 1)
        self.assertEqual(body["items"][0]["id"], 3)

    def test_list_stations_filters_by_province(self):
        response = self.client.get("/api/v1/stations", params={"province": "benguela"})
        body = response.json()
        self.assertEqual(body["total"], 1)
        self.assertEqual(body["items"][0]["station"], "Sonangol Benguela")

    def test_province_filter_is_exact_match(self):
        response = self.client.get("/api/v1/stations", params={"province": "enguela"})
        body = response.json()
        self.assertEqual(body["total"], 0)
        self.assertEqual(body["items"], [])

    def test_filter_with_no_match_returns_empty(self):
        response = self.client.get("/api/v1/stations", params={"operator": "Nope"})
        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["total"], 0)

    def test_filter_with_regex_chars_does_not_500(self):
        for params in ({"province": "("}, {"operator": ".*"}, {"search": "[a-z"}):
            response = self.client.get("/api/v1/stations", params=params)
            self.assertEqual(response.status_code, 200, f"params={params}")

    def test_list_stations_searches_name_and_address(self):
        response = self.client.get("/api/v1/stations", params={"search": "viana"})
        body = response.json()
        self.assertEqual(body["total"], 1)
        self.assertEqual(body["items"][0]["operator"], "Pumangol")

    def test_get_station_returns_detail(self):
        response = self.client.get("/api/v1/stations/1")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["station"], "Sonangol Cazenga")
        self.assertAlmostEqual(body["latitude"], -8.8)

    def test_get_station_unknown_id_returns_404(self):
        response = self.client.get("/api/v1/stations/999")
        self.assertEqual(response.status_code, 404)

    def test_stats_aggregates(self):
        response = self.client.get("/api/v1/stations/stats")
        body = response.json()
        self.assertEqual(body["total_stations"], 3)
        self.assertEqual(body["with_coordinates"], 3)
        self.assertEqual(body["by_operator"], {"Sonangol": 2, "Pumangol": 1})
        self.assertEqual(body["by_province"], {"Luanda": 2, "Benguela": 1})

    def test_provinces_and_operators_lists(self):
        provinces = self.client.get("/api/v1/stations/provinces").json()
        operators = self.client.get("/api/v1/stations/operators").json()
        self.assertEqual(provinces, ["Benguela", "Luanda"])
        self.assertEqual(operators, ["Pumangol", "Sonangol"])

    def test_page_size_is_capped(self):
        response = self.client.get("/api/v1/stations", params={"page_size": 500})
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
