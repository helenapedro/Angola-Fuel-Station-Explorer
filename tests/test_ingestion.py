import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
import json

from ingestion.normalize import clean_text, normalize_legacy_pumangol
from ingestion.sources.sonangol import normalize_sonangol_payload
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

    def test_sonangol_osm_fixture_is_normalized(self):
        fixture_path = Path(__file__).parent / "fixtures" / "sonangol_osm_response.json"
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))

        records = normalize_sonangol_payload(payload, scraped_at="2026-07-10T00:00:00+00:00")

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["operator"], "Sonangol")
        self.assertEqual(records[0]["station"], "Sonangol Maianga")
        self.assertEqual(records[0]["source_type"], "openstreetmap_operator")
        self.assertEqual(records[0]["source_name"], "SonangolOpenStreetMap")


class DataQualityGatesTest(unittest.TestCase):
    def _record(self, **overrides):
        record = {
            "operator": "Unknown",
            "station": "Some station",
            "address": "",
            "province": "Luanda",
            "municipality": "Luanda",
            "country": "Angola",
            "latitude": -8.83,
            "longitude": 13.24,
            "source_type": "openstreetmap",
            "source_name": "OpenStreetMap",
            "source_id": "node/1",
        }
        record.update(overrides)
        return record

    def test_registry_contains_only_verified_brands(self):
        from ingestion.operators import CANONICAL_OPERATORS

        self.assertEqual(
            set(CANONICAL_OPERATORS),
            {"Sonangol", "Pumangol", "TotalEnergies", "Sonangalp", "Etu Energias"},
        )

    def test_etu_energias_aliases(self):
        from ingestion.operators import canonicalize_operator

        self.assertEqual(canonicalize_operator("Etu Energias"), "Etu Energias")
        self.assertEqual(canonicalize_operator("Somoil"), "Etu Energias")
        # Bare "etu" means "us/ours" in Bantu languages and shows up in
        # ordinary station names: never map it to the brand.
        self.assertEqual(canonicalize_operator("Etu"), "Unknown")
        self.assertEqual(canonicalize_operator("", "Posto Etu Kwanza"), "Unknown")

    def test_colloquial_brand_variants(self):
        from ingestion.operators import canonicalize_operator

        self.assertEqual(canonicalize_operator("", "Pumangola"), "Pumangol")
        self.assertEqual(
            canonicalize_operator("", "Posto de combustível da Sonangola"),
            "Sonangol",
        )

    def test_osm_brand_tag_takes_precedence_over_operator(self):
        from ingestion.normalize import normalize_osm_element

        element = {
            "type": "way",
            "id": 1130685470,
            "tags": {
                "amenity": "fuel",
                "brand": "TotalEnergies",
                "name": "TotalEnergies",
                "operator": "P.A. Kindombele",
            },
            "center": {"lat": -6.16, "lon": 12.37},
        }
        record = normalize_osm_element(element)
        # OSM `brand` is the marketed flag; `operator` is the franchisee.
        self.assertEqual(record["operator"], "TotalEnergies")

    def test_osm_operator_used_when_brand_missing(self):
        from ingestion.normalize import normalize_osm_element

        element = {
            "type": "node",
            "id": 1,
            "lat": -8.83,
            "lon": 13.24,
            "tags": {"amenity": "fuel", "name": "X", "operator": "Sonangol"},
        }
        self.assertEqual(normalize_osm_element(element)["operator"], "Sonangol")

    def test_operator_variants_canonicalize(self):
        from ingestion.operators import canonicalize_operator

        cases = {
            "Pumangol": "Pumangol",
            "Puma": "Pumangol",
            "Puma Energy": "Pumangol",
            "PUMANGOL": "Pumangol",
            "pumangol": "Pumangol",
            "Sonagol": "Sonangol",
            "Sonagalp": "Sonangalp",
            "TotalEnergies Marketing & Services Angola, S.A.": "TotalEnergies",
            "Pumangol, Lda.": "Pumangol",
        }
        for raw, expected in cases.items():
            self.assertEqual(canonicalize_operator(raw), expected, raw)

    def test_unknown_operator_stays_unknown(self):
        from ingestion.operators import canonicalize_operator

        self.assertEqual(canonicalize_operator(""), "Unknown")
        self.assertEqual(canonicalize_operator(None), "Unknown")
        self.assertEqual(canonicalize_operator("Some Random Brand"), "Unknown")

    def test_operator_inferred_from_station_name(self):
        from ingestion.operators import canonicalize_operator

        self.assertEqual(
            canonicalize_operator("Unknown", "TotalEnergies - P.A. BOA ENTRADA"),
            "TotalEnergies",
        )
        # An explicit (even wrong-looking) tag is never overridden by the name.
        self.assertEqual(canonicalize_operator("Pumangol", "Sonangol Maianga"), "Pumangol")

    def test_merge_osm_id_duplicate_into_branded_record(self):
        branded = self._record(
            operator="Sonangol",
            station="Sonangol",
            source_type="openstreetmap_operator",
            source_name="SonangolOpenStreetMap",
            latitude=-8.8300,
            longitude=13.2400,
        )
        unnamed = self._record(
            station="way/954638665",
            latitude=-8.8305,  # ~55 m away
            longitude=13.2405,
        )

        clean, rejected = split_valid_records([branded, unnamed])

        self.assertEqual(rejected, [])
        self.assertEqual(len(clean), 1)
        self.assertEqual(clean[0]["station"], "Sonangol")
        self.assertEqual(clean[0]["operator"], "Sonangol")
        self.assertEqual(
            clean[0]["merged_sources"], ["OpenStreetMap", "SonangolOpenStreetMap"]
        )

    def test_different_brands_close_together_do_not_merge(self):
        sonangol = self._record(
            operator="Sonangol", station="Sonangol X", latitude=-8.83, longitude=13.24
        )
        pumangol = self._record(
            operator="Pumangol",
            station="Pumangol Y",
            latitude=-8.8305,  # ~55 m away, across the street
            longitude=13.2405,
        )

        deduped = deduplicate_records([sonangol, pumangol])

        self.assertEqual(len(deduped), 2)

    def test_same_brand_far_apart_does_not_merge(self):
        first = self._record(
            operator="Sonangol", station="Sonangol X", latitude=-8.83, longitude=13.24
        )
        second = self._record(
            operator="Sonangol",
            station="Sonangol Y",
            latitude=-8.84,  # ~1.1 km away: a different site
            longitude=13.25,
        )

        deduped = deduplicate_records([first, second])

        self.assertEqual(len(deduped), 2)

    def test_lone_osm_id_name_is_rejected(self):
        unnamed = self._record(station="node/123456")

        clean, rejected = split_valid_records([unnamed])

        self.assertEqual(clean, [])
        self.assertEqual(len(rejected), 1)
        self.assertIn("station name is an OSM element id", rejected[0]["rejection_reasons"])

    def test_brand_variants_merge_into_one_station(self):
        variant_a = self._record(
            operator="pumangol", station="Panguila", latitude=-8.681717, longitude=13.469734
        )
        variant_b = self._record(
            operator="Puma Energy",
            station="Panguila",
            latitude=-8.681800,  # ~10 m away
            longitude=13.469800,
        )

        clean, _ = split_valid_records([variant_a, variant_b])

        self.assertEqual(len(clean), 1)
        self.assertEqual(clean[0]["operator"], "Pumangol")


class ProvinceBackfillTest(unittest.TestCase):
    def test_fills_province_from_municipality(self):
        from ingestion.provinces import backfill_province

        cases = {
            "Luanda": "Luanda",
            "Lubango": "Huila",
            "Ondjiva": "Cunene",
            "Quibala": "Kwanza Sul",
            "Panguila": "Bengo",
            "Moçâmedes": "Namibe",
            "Malanje": "Malange",  # dataset spelling
            "Caconda": "Huila",
            "Alto Hama": "Huambo",
        }
        for municipality, expected in cases.items():
            record, filled = backfill_province(
                {"province": "", "municipality": municipality}
            )
            self.assertTrue(filled, municipality)
            self.assertEqual(record["province"], expected, municipality)
            self.assertTrue(record["province_inferred"], municipality)

    def test_does_not_overwrite_tagged_province(self):
        from ingestion.provinces import backfill_province

        record, filled = backfill_province(
            {"province": "Benguela", "municipality": "Luanda"}
        )
        self.assertFalse(filled)
        self.assertEqual(record["province"], "Benguela")
        self.assertFalse(record["province_inferred"])

    def test_ambiguous_or_reform_affected_stays_empty(self):
        from ingestion.provinces import backfill_province

        for municipality in ("", "Bairro da Luz", "Funda", "Botomona"):
            record, filled = backfill_province(
                {"province": "", "municipality": municipality}
            )
            self.assertFalse(filled, municipality)
            self.assertEqual(record["province"], "", municipality)
            self.assertFalse(record["province_inferred"], municipality)

    def test_backfill_runs_inside_split_valid_records(self):
        record = {
            "operator": "Unknown",
            "station": "Bombas de Gasolina dos Chineses",
            "address": "Avenida Deolinda Rodrigues, Luanda",
            "province": "",
            "municipality": "Luanda",
            "country": "Angola",
            "latitude": -8.8759079,
            "longitude": 13.3269486,
            "source_type": "openstreetmap",
            "source_name": "OpenStreetMap",
            "source_id": "node/999",
        }
        clean, _ = split_valid_records([record])
        self.assertEqual(clean[0]["province"], "Luanda")
        self.assertTrue(clean[0]["province_inferred"])

    def test_inferred_flag_survives_reprocessing(self):
        # Stale records re-enter the pipeline on flaky-network runs; a
        # previously inferred province must keep its provenance.
        from ingestion.provinces import backfill_province

        record, filled = backfill_province(
            {
                "province": "Luanda",
                "municipality": "Luanda",
                "province_inferred": True,
            }
        )
        self.assertFalse(filled)
        self.assertEqual(record["province"], "Luanda")
        self.assertTrue(record["province_inferred"])

    def test_count_backfilled(self):
        from ingestion.provinces import backfill_province, count_backfilled

        records = [
            {"province": "", "municipality": "Luanda"},
            {"province": "Huila", "municipality": "Lubango"},  # tagged
            {"province": "", "municipality": "Nowhere"},
        ]
        filled = [backfill_province(r)[0] for r in records]
        self.assertEqual(count_backfilled(filled), 1)


class StaleReuseTest(unittest.TestCase):
    def _base_record(self, **overrides):
        record = {
            "operator": "Sonangol",
            "station": "Posto Teste",
            "address": "Luanda",
            "province": "",
            "municipality": "Luanda",
            "country": "Angola",
            "latitude": -8.8,
            "longitude": 13.2,
            "source_type": "openstreetmap",
            "source_name": "OpenStreetMap",
            "source_id": "node/1",
        }
        record.update(overrides)
        return record

    def test_failed_source_reuses_previous_rejected_records(self):
        import json
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        from ingestion import sync_stations

        clean_prev = {
            "metadata": {},
            "stations": [self._base_record()],
        }
        rejected_prev = {
            "metadata": {},
            "stations": [
                self._base_record(
                    station="way/1",
                    source_id="way/1",
                    latitude=-9.0,  # far away: must not merge into node/1
                    longitude=13.5,
                    rejection_reasons=["osm id as station name"],
                )
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            clean_path = Path(tmp) / "clean.json"
            rejected_path = Path(tmp) / "rejected.json"
            clean_path.write_text(json.dumps(clean_prev), encoding="utf-8")
            rejected_path.write_text(json.dumps(rejected_prev), encoding="utf-8")

            def boom():
                raise RuntimeError("network down")

            with (
                patch(
                    "ingestion.sources.osm.fetch_osm_stations", side_effect=boom
                ),
                patch(
                    "ingestion.sources.sonangol.fetch_sonangol_stations",
                    side_effect=boom,
                ),
                patch(
                    "ingestion.sources.pumangol.fetch_pumangol_stations",
                    side_effect=boom,
                ),
                patch.object(
                    sync_stations,
                    "LEGACY_FALLBACK_PATH",
                    Path(tmp) / "no-legacy.json",
                ),
            ):
                clean, rejected = sync_stations.build_dataset(
                    include_network_sources=True,
                    previous_clean_path=clean_path,
                    previous_rejected_path=rejected_path,
                )

        # The stale clean record survives (with backfilled province)...
        self.assertEqual(len(clean["stations"]), 1)
        self.assertEqual(clean["stations"][0]["province"], "Luanda")
        # ...and the stale rejected record is re-rejected, not lost.
        self.assertEqual(len(rejected["stations"]), 1)
        way = rejected["stations"][0]
        self.assertEqual(way["source_id"], "way/1")
        self.assertTrue(way["is_stale"])
        self.assertTrue(
            any("OSM element id" in r for r in way["rejection_reasons"]),
            way["rejection_reasons"],
        )


if __name__ == "__main__":
    unittest.main()
