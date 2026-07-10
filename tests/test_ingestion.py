import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
import json

from ingestion.normalize import clean_text, normalize_legacy_pumangol
from ingestion.sync_stations import _load_previous_source_records, build_dataset
from ingestion.validate import deduplicate_records, split_valid_records, validate_station


class IngestionValidationTest(unittest.TestCase):
    def test_rejects_null_island_coordinates(self):
        record = normalize_legacy_pumangol(
            {
                "name": "Caxito",
                "address": "Bairro do Kixiquela",
                "city": "Caxito - Dande",
                "state": "Bengo",
                "country": "Angola",
                "latitude": 0,
                "longitude": 0,
            },
            scraped_at="2026-07-10T00:00:00+00:00",
        )

        _, reasons = validate_station(record)

        self.assertIn("null island coordinates", reasons)

    def test_keeps_valid_angola_station(self):
        record = normalize_legacy_pumangol(
            {
                "name": "Panguila",
                "address": "Luanda",
                "city": "Panguila - Cacuaco",
                "state": "Bengo",
                "country": "Angola",
                "latitude": -8.681717,
                "longitude": 13.469734,
            },
            scraped_at="2026-07-10T00:00:00+00:00",
        )

        clean_records, rejected_records = split_valid_records([record])

        self.assertEqual(len(clean_records), 1)
        self.assertEqual(rejected_records, [])

    def test_clean_text_decodes_html_entities(self):
        self.assertEqual(clean_text("M&#039;banza   Congo"), "M'banza Congo")

    def test_deduplicate_prefers_fresh_operator_record(self):
        osm_record = {
            "operator": "Pumangol",
            "station": "Panguila",
            "address": "",
            "province": "Bengo",
            "municipality": "Cacuaco",
            "country": "Angola",
            "latitude": -8.681717,
            "longitude": 13.469734,
            "source_type": "openstreetmap",
            "source_name": "OpenStreetMap",
            "source_id": "node/1",
        }
        operator_record = {
            **osm_record,
            "address": "Operator supplied address",
            "source_type": "operator_website",
            "source_name": "Pumangol",
            "source_id": "Panguila",
        }

        deduped = deduplicate_records([osm_record, operator_record])

        self.assertEqual(len(deduped), 1)
        self.assertEqual(deduped[0]["source_name"], "Pumangol")
        self.assertEqual(deduped[0]["address"], "Operator supplied address")

    def test_previous_source_records_are_marked_stale(self):
        with TemporaryDirectory() as temp_dir:
            clean_path = Path(temp_dir) / "stations_clean.json"
            clean_path.write_text(
                json.dumps(
                    {
                        "stations": [
                            {"source_name": "Pumangol", "station": "A"},
                            {"source_name": "OpenStreetMap", "station": "B"},
                        ]
                    }
                ),
                encoding="utf-8",
            )

            stale_records = _load_previous_source_records(clean_path, "Pumangol", "timeout")

        self.assertEqual(len(stale_records), 1)
        self.assertTrue(stale_records[0]["is_stale"])
        self.assertEqual(stale_records[0]["stale_reason"], "timeout")

    def test_offline_dataset_reports_legacy_source_status(self):
        clean_payload, rejected_payload = build_dataset(include_network_sources=False)

        self.assertIn("source_status", clean_payload["metadata"])
        self.assertEqual(clean_payload["metadata"]["source_status"][0]["source"], "BundledLegacyPumangol")
        self.assertEqual(clean_payload["metadata"]["record_count"], len(clean_payload["stations"]))
        self.assertEqual(rejected_payload["metadata"]["rejected_count"], len(rejected_payload["stations"]))


if __name__ == "__main__":
    unittest.main()
