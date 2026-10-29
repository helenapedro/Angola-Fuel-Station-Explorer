"""Tests for GET /api/v1/meta: the public metadata contract."""

import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

import dataset_meta
from api.deps import get_station_data
from api.main import app


class MetaApiTest(unittest.TestCase):
    def setUp(self):
        app.dependency_overrides[get_station_data] = (
            lambda: (pd.DataFrame([{"id": 1}]), "live")
        )
        dataset_meta.clear_dataset_meta_cache()
        self.client = TestClient(app)
        self._tmp = tempfile.TemporaryDirectory()
        self._original_path = dataset_meta.CLEAN_DATA_PATH

    def tearDown(self):
        app.dependency_overrides.clear()
        dataset_meta.clear_dataset_meta_cache()
        dataset_meta.CLEAN_DATA_PATH = self._original_path
        self._tmp.cleanup()

    def _fixture(self, metadata):
        path = Path(self._tmp.name) / "stations_clean.json"
        path.write_text(json.dumps({"metadata": metadata}), encoding="utf-8")
        dataset_meta.CLEAN_DATA_PATH = path
        return path

    def test_meta_returns_snapshot_fields(self):
        self._fixture(
            {
                "generated_at": "2026-09-23T11:27:12+00:00",
                "record_count": 279,
                "rejected_count": 63,
                "source_status": [
                    {
                        "source": "OpenStreetMap",
                        "status": "stale_reused",
                        "record_count": 187,
                        "is_stale": True,
                        "error": "must not be exposed",
                    }
                ],
            }
        )
        body = self.client.get("/api/v1/meta").json()
        self.assertEqual(body["generated_at"], "2026-09-23T11:27:12+00:00")
        self.assertEqual(body["version_id"], "2026-09-23T11:27:12+00:00")
        self.assertEqual(body["record_count"], 279)
        self.assertEqual(body["rejected_count"], 63)
        self.assertEqual(body["source"], "live")
        self.assertEqual(body["freshness_status"], "overdue")
        self.assertEqual(body["fresh_threshold_days"], 14)
        self.assertIsNone(body["confidence_counts"])
        # No internal error text leaks into the public response.
        self.assertNotIn("must not be exposed", json.dumps(body))
        self.assertEqual(
            body["source_status"],
            [
                {
                    "source": "OpenStreetMap",
                    "status": "stale_reused",
                    "record_count": 187,
                    "is_stale": True,
                }
            ],
        )

    def test_meta_missing_snapshot_is_unavailable_not_500(self):
        dataset_meta.CLEAN_DATA_PATH = Path(self._tmp.name) / "missing.json"
        response = self.client.get("/api/v1/meta")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIsNone(body["generated_at"])
        self.assertEqual(body["freshness_status"], "unavailable")
        self.assertFalse(body["fresh"])

    def test_api_index_lists_meta(self):
        endpoints = self.client.get("/api/v1").json()["endpoints"]
        self.assertIn("GET /api/v1/meta", endpoints)


if __name__ == "__main__":
    unittest.main()
