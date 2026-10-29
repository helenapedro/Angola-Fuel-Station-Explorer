"""Tests for dataset_meta: freshness is derived from generated_at only."""

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import dataset_meta


def _write_snapshot(directory, metadata):
    path = Path(directory) / "stations_clean.json"
    path.write_text(json.dumps({"metadata": metadata}), encoding="utf-8")
    return path


def _meta(**overrides):
    base = {
        "generated_at": "2026-09-23T11:27:12+00:00",
        "record_count": 279,
        "rejected_count": 63,
        "source_status": [
            {
                "source": "OpenStreetMap",
                "status": "stale_reused",
                "record_count": 187,
                "is_stale": True,
                "error": "connection failed (must not be exposed)",
            }
        ],
    }
    base.update(overrides)
    return base


class DatasetMetaTest(unittest.TestCase):
    def setUp(self):
        dataset_meta.clear_dataset_meta_cache()

    def tearDown(self):
        dataset_meta.clear_dataset_meta_cache()

    def test_freshness_boundaries(self):
        self.assertEqual(dataset_meta.freshness_status(None), "unavailable")
        self.assertEqual(dataset_meta.freshness_status(0), "fresh")
        self.assertEqual(dataset_meta.freshness_status(14), "fresh")
        self.assertEqual(dataset_meta.freshness_status(15), "stale")
        self.assertEqual(dataset_meta.freshness_status(28), "stale")
        self.assertEqual(dataset_meta.freshness_status(29), "overdue")

    def test_missing_file_returns_none(self):
        self.assertIsNone(
            dataset_meta.load_dataset_meta(
                datetime(2026, 10, 28, tzinfo=timezone.utc),
                data_path="/tmp/does-not-exist-stations-clean.json",
            )
        )

    def test_invalid_json_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "stations_clean.json"
            path.write_text("{not json", encoding="utf-8")
            self.assertIsNone(
                dataset_meta.load_dataset_meta(
                    datetime(2026, 10, 28, tzinfo=timezone.utc), data_path=path
                )
            )

    def test_snapshot_age_and_sanitised_source_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_snapshot(tmp, _meta())
            now = datetime(2026, 10, 28, 12, 0, tzinfo=timezone.utc)
            meta = dataset_meta.load_dataset_meta(now, data_path=path)
        self.assertEqual(meta["generated_at"], "2026-09-23T11:27:12+00:00")
        self.assertEqual(meta["version_id"], "2026-09-23T11:27:12+00:00")
        self.assertEqual(meta["age_days"], 35)
        self.assertEqual(meta["freshness_status"], "overdue")
        self.assertFalse(meta["fresh"])
        self.assertTrue(meta["is_stale"])
        self.assertEqual(meta["record_count"], 279)
        self.assertEqual(meta["rejected_count"], 63)
        # Error text is stripped from the public source status.
        self.assertEqual(
            meta["source_status"],
            [
                {
                    "source": "OpenStreetMap",
                    "status": "stale_reused",
                    "record_count": 187,
                    "is_stale": True,
                }
            ],
        )
        # The current snapshot has no confidence counts yet: null, not zero.
        self.assertIsNone(meta["confidence_counts"])

    def test_future_generated_at_is_unavailable_not_negative_age(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_snapshot(tmp, _meta(generated_at="2027-01-01T00:00:00+00:00"))
            meta = dataset_meta.load_dataset_meta(
                datetime(2026, 10, 28, tzinfo=timezone.utc), data_path=path
            )
        self.assertIsNone(meta["age_days"])
        self.assertEqual(meta["freshness_status"], "unavailable")
        self.assertFalse(meta["fresh"])

    def test_invalid_generated_at_is_unavailable(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_snapshot(tmp, _meta(generated_at="not-a-date"))
            meta = dataset_meta.load_dataset_meta(
                datetime(2026, 10, 28, tzinfo=timezone.utc), data_path=path
            )
        self.assertIsNone(meta["age_days"])
        self.assertEqual(meta["freshness_status"], "unavailable")

    def test_badge_text(self):
        fresh = {
            "generated_at": "2026-10-28T00:00:00+00:00",
            "age_days": 0,
            "freshness_status": "fresh",
        }
        stale = {
            "generated_at": "2026-10-10T00:00:00+00:00",
            "age_days": 18,
            "freshness_status": "stale",
        }
        overdue = {
            "generated_at": "2026-09-23T11:27:12+00:00",
            "age_days": 35,
            "freshness_status": "overdue",
        }
        self.assertEqual(
            dataset_meta.format_dataset_badge(fresh),
            ("Updated on 28/10/2026 (0 days ago).", "fresh"),
        )
        self.assertEqual(
            dataset_meta.format_dataset_badge(stale),
            ("Updated on 10/10/2026 (18 days ago). Data is outdated.", "stale"),
        )
        self.assertEqual(
            dataset_meta.format_dataset_badge(overdue),
            ("Updated on 23/09/2026 (35 days ago). Data is overdue.", "overdue"),
        )
        self.assertEqual(
            dataset_meta.format_dataset_badge(None),
            ("Dataset update date unavailable.", "unavailable"),
        )


if __name__ == "__main__":
    unittest.main()
