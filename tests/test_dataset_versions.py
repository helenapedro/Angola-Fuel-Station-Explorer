"""Tests for the dataset version registry and confidence aggregates."""

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import dataset_versions
from dataset_versions import (
    append_version_entry,
    build_version_entry,
    confidence_counts,
    confidence_level,
    freshness_status_at,
    load_dataset_versions,
    read_versions_file,
)

NOW = datetime(2026, 10, 5, 6, 0, tzinfo=timezone.utc)

META = {
    "generated_at": "2026-10-05T06:00:00+00:00",
    "record_count": 279,
    "rejected_count": 63,
    "source_status": [
        {"source": "OpenStreetMap", "status": "loaded", "record_count": 187, "is_stale": False}
    ],
}


class ConfidenceTest(unittest.TestCase):
    def test_level_mapping(self):
        self.assertEqual(confidence_level({"source_type": "operator_website"}), "operador_via_listagem_publica")
        self.assertEqual(confidence_level({"source_type": "openstreetmap_operator"}), "operador_via_osm")
        self.assertEqual(confidence_level({"source_type": "openstreetmap"}), "base_publica_osm")
        self.assertEqual(confidence_level({"source_type": "legacy_snapshot"}), "base_publica_osm")
        self.assertEqual(confidence_level({}), "base_publica_osm")

    def test_stale_does_not_change_level(self):
        self.assertEqual(
            confidence_level({"source_type": "operator_website", "is_stale": True}),
            "operador_via_listagem_publica",
        )

    def test_counts_sum_to_record_count(self):
        records = [
            {"source_type": "operator_website"},
            {"source_type": "openstreetmap_operator"},
            {"source_type": "openstreetmap"},
            {"source_type": "legacy_snapshot"},
        ]
        counts = confidence_counts(records)
        self.assertEqual(sum(counts.values()), len(records))
        self.assertEqual(counts["operador_via_listagem_publica"], 1)
        self.assertEqual(counts["operador_via_osm"], 1)
        self.assertEqual(counts["base_publica_osm"], 2)


class VersionEntryTest(unittest.TestCase):
    def test_entry_uses_generated_at_as_version_id(self):
        entry = build_version_entry(META, now=NOW)
        self.assertEqual(entry["version_id"], "2026-10-05T06:00:00+00:00")
        self.assertEqual(entry["freshness_status_at_publication"], "fresh")
        self.assertEqual(entry["record_count"], 279)
        self.assertEqual(entry["source_status_summary"][0]["source"], "OpenStreetMap")

    def test_freshness_at_publication_boundaries(self):
        self.assertEqual(freshness_status_at("2026-10-05T06:00:00+00:00", NOW), "fresh")
        self.assertEqual(freshness_status_at("2026-09-20T06:00:00+00:00", NOW), "stale")
        self.assertEqual(freshness_status_at("2026-09-01T06:00:00+00:00", NOW), "overdue")
        self.assertEqual(freshness_status_at("2026-10-06T06:00:00+00:00", NOW), "unknown")
        self.assertEqual(freshness_status_at("not-a-date", NOW), "unknown")
        self.assertEqual(freshness_status_at(None, NOW), "unknown")

    def test_append_is_idempotent_and_never_rewrites(self):
        versions, _, appended = append_version_entry([], META, now=NOW)
        self.assertTrue(appended)
        self.assertEqual(len(versions), 1)
        first = dict(versions[0])
        changed_meta = dict(META, record_count=999)
        versions2, _, appended2 = append_version_entry(versions, changed_meta, now=NOW)
        self.assertFalse(appended2)
        self.assertEqual(versions2[0], first)

    def test_append_keeps_old_entries_unchanged(self):
        versions, _, _ = append_version_entry([], META, now=NOW)
        second = dict(META, generated_at="2026-10-12T06:00:00+00:00", record_count=280)
        versions, _, _ = append_version_entry(versions, second, now=datetime(2026, 10, 12, 6, tzinfo=timezone.utc))
        self.assertEqual(len(versions), 2)
        self.assertEqual(versions[0]["record_count"], 279)
        self.assertEqual(versions[1]["record_count"], 280)


class LoadVersionsTest(unittest.TestCase):
    def test_missing_file_falls_back_to_current_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "dataset_versions.json"
            versions = load_dataset_versions(versions_path=missing, meta=META, now=NOW)
            self.assertEqual(len(versions), 1)
            self.assertEqual(versions[0]["version_id"], META["generated_at"])
            self.assertEqual(versions[0]["freshness_status_at_publication"], "unknown")

    def test_missing_file_and_no_meta_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(
                load_dataset_versions(versions_path=Path(tmp) / "nope.json", meta=None), []
            )

    def test_recorded_file_is_returned_as_is(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dataset_versions.json"
            entry = build_version_entry(META, now=NOW)
            path.write_text(json.dumps([entry]), encoding="utf-8")
            self.assertEqual(load_dataset_versions(versions_path=path, meta=META), [entry])
            self.assertEqual(read_versions_file(path), [entry])

    def test_corrupt_file_falls_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dataset_versions.json"
            path.write_text("{not json", encoding="utf-8")
            versions = load_dataset_versions(versions_path=path, meta=META, now=NOW)
            self.assertEqual(len(versions), 1)
            self.assertEqual(read_versions_file(path), [])
