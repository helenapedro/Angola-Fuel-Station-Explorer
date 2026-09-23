"""Tests for the geocoding backfill (ingestion/geocode.py)."""

import unittest
from unittest.mock import MagicMock, patch

from ingestion.geocode import (
    ADDRESS_SOURCE_PLUS_CODE,
    NominatimClient,
    backfill_geocode,
    clean_municipality,
    clean_province,
    compound_address,
    station_plus_code,
)
from ingestion.validate import deduplicate_records


def _record(**overrides):
    record = {
        "station": "Posto Teste",
        "operator": "Sonangol",
        "latitude": -7.7602146,
        "longitude": 15.2694335,
        "address": "",
        "municipality": "",
        "province": "",
    }
    record.update(overrides)
    return record


def _nominatim_response(address):
    response = MagicMock()
    response.json.return_value = {"address": address}
    response.raise_for_status.return_value = None
    return response


class PlusCodeTest(unittest.TestCase):
    def test_helena_example_matches_google(self):
        # Helena verified on Google Maps: -7.7602146, 15.2694335 is
        # "67Q9+WQ7 Negage, Angola".
        self.assertEqual(
            station_plus_code(-7.7602146, 15.2694335), "6F4Q67Q9+WQ7"
        )

    def test_compound_address_with_locality(self):
        self.assertEqual(
            compound_address(-7.7602146, 15.2694335, "Negage"),
            "67Q9+WQ7 Negage, Angola",
        )

    def test_compound_address_without_locality_falls_back_to_full_code(self):
        for locality in (None, "", "   "):
            self.assertEqual(
                compound_address(-7.7602146, 15.2694335, locality),
                "6F4Q67Q9+WQ7",
            )

    def test_plus_code_is_deterministic(self):
        self.assertEqual(
            station_plus_code(-8.8383, 13.2344),
            station_plus_code(-8.8383, 13.2344),
        )


class CleanProvinceTest(unittest.TestCase):
    def test_strips_province_suffix(self):
        self.assertEqual(clean_province("Icolo e Bengo Province"), "Icolo e Bengo")

    def test_normalizes_to_dataset_spellings(self):
        self.assertEqual(clean_province("Uíge"), "Uige")
        self.assertEqual(clean_province("Malanje"), "Malange")
        self.assertEqual(clean_province("Cuando Cubango"), "Kuando Kubango")
        self.assertEqual(clean_province("Bié"), "Bie")
        self.assertEqual(clean_province("Huíla"), "Huila")
        self.assertEqual(clean_province("Cuanza Sul"), "Kwanza Sul")

    def test_unknown_province_passes_through(self):
        self.assertEqual(clean_province("Moxico"), "Moxico")

    def test_empty_stays_empty(self):
        self.assertEqual(clean_province(""), "")
        self.assertEqual(clean_province(None), "")


class CleanMunicipalityTest(unittest.TestCase):
    def test_strips_municipio_prefix(self):
        self.assertEqual(clean_municipality("Município do Belas"), "Belas")
        self.assertEqual(clean_municipality("Município de Luanda"), "Luanda")
        self.assertEqual(clean_municipality("Município de Ícolo e Bengo"), "Ícolo e Bengo")

    def test_plain_names_pass_through(self):
        self.assertEqual(clean_municipality("Negage"), "Negage")

    def test_empty_stays_empty(self):
        self.assertEqual(clean_municipality(""), "")


class NominatimClientTest(unittest.TestCase):
    def _client(self):
        return NominatimClient(cache_path=None, throttle_seconds=0)

    @patch("ingestion.geocode.requests.get")
    def test_parses_municipality_and_province(self, mock_get):
        mock_get.return_value = _nominatim_response(
            {"county": "Município do Belas", "state": "Luanda", "country": "Angola"}
        )
        result = self._client().reverse(-9.10, 13.15)
        self.assertEqual(
            result, {"province": "Luanda", "municipality": "Belas"}
        )

    @patch("ingestion.geocode.requests.get")
    def test_town_falls_back_when_no_county(self, mock_get):
        mock_get.return_value = _nominatim_response(
            {"town": "Negage", "state": "Uíge", "country": "Angola"}
        )
        result = self._client().reverse(-7.7602146, 15.2694335)
        self.assertEqual(result, {"province": "Uige", "municipality": "Negage"})

    @patch("ingestion.geocode.requests.get")
    def test_county_beats_town(self, mock_get):
        mock_get.return_value = _nominatim_response(
            {
                "town": "Catete",
                "county": "Município de Ícolo e Bengo",
                "state": "Icolo e Bengo Province",
            }
        )
        result = self._client().reverse(-9.1167, 13.6833)
        self.assertEqual(
            result,
            {"province": "Icolo e Bengo", "municipality": "Ícolo e Bengo"},
        )

    @patch("ingestion.geocode.requests.get")
    def test_suburb_is_not_a_municipality(self, mock_get):
        mock_get.return_value = _nominatim_response(
            {"suburb": "Martires de Kifangondo", "country": "Angola"}
        )
        self.assertIsNone(self._client().reverse(-8.8383, 13.2344))

    @patch("ingestion.geocode.requests.get")
    def test_caches_results(self, mock_get):
        mock_get.return_value = _nominatim_response(
            {"town": "Negage", "state": "Uíge"}
        )
        client = self._client()
        first = client.reverse(-7.7602146, 15.2694335)
        second = client.reverse(-7.7602146, 15.2694335)
        self.assertEqual(first, second)
        mock_get.assert_called_once()

    @patch("ingestion.geocode.requests.get")
    def test_network_failure_returns_none(self, mock_get):
        mock_get.side_effect = Exception("boom")
        self.assertIsNone(self._client().reverse(-7.7602146, 15.2694335))

    def test_invalid_coordinates_return_none(self):
        client = self._client()
        self.assertIsNone(client.reverse(None, 15.0))
        self.assertIsNone(client.reverse("x", 15.0))


class BackfillGeocodeTest(unittest.TestCase):
    def test_never_overwrites_existing_values(self):
        record = _record(
            address="Rua X", municipality="Luanda", province="Luanda"
        )
        client = MagicMock()
        filled, stats = backfill_geocode([record], client=client)
        self.assertEqual(filled[0]["address"], "Rua X")
        self.assertEqual(filled[0]["municipality"], "Luanda")
        self.assertEqual(filled[0]["province"], "Luanda")
        self.assertFalse(filled[0].get("municipality_inferred"))
        self.assertFalse(filled[0].get("province_inferred"))
        self.assertNotIn("address_source", filled[0])
        client.reverse.assert_not_called()
        self.assertEqual(
            stats,
            {"address_filled": 0, "municipality_filled": 0, "province_filled": 0},
        )

    def test_fills_address_with_compound_plus_code(self):
        record = _record(municipality="Negage")
        filled, stats = backfill_geocode([record], client=None)
        self.assertEqual(filled[0]["address"], "67Q9+WQ7 Negage, Angola")
        self.assertEqual(filled[0]["address_source"], ADDRESS_SOURCE_PLUS_CODE)
        self.assertEqual(stats["address_filled"], 1)

    def test_fills_address_with_full_plus_code_without_municipality(self):
        record = _record()
        filled, _ = backfill_geocode([record], client=None)
        self.assertEqual(filled[0]["address"], "6F4Q67Q9+WQ7")

    def test_offline_mode_skips_nominatim(self):
        record = _record()
        filled, stats = backfill_geocode([record], client=None)
        self.assertEqual(filled[0]["municipality"], "")
        self.assertEqual(filled[0]["province"], "")
        self.assertEqual(stats["municipality_filled"], 0)
        self.assertEqual(stats["province_filled"], 0)

    def test_nominatim_fills_municipality_and_province(self):
        client = MagicMock()
        client.reverse.return_value = {
            "province": "Uige",
            "municipality": "Negage",
        }
        filled, stats = backfill_geocode([_record()], client=client)
        self.assertEqual(filled[0]["municipality"], "Negage")
        self.assertTrue(filled[0]["municipality_inferred"])
        self.assertEqual(filled[0]["province"], "Uige")
        self.assertTrue(filled[0]["province_inferred"])
        # Compound address uses the freshly backfilled municipality.
        self.assertEqual(filled[0]["address"], "67Q9+WQ7 Negage, Angola")
        self.assertEqual(stats["municipality_filled"], 1)
        self.assertEqual(stats["province_filled"], 1)

    def test_nominatim_failure_leaves_fields_empty_but_fills_address(self):
        client = MagicMock()
        client.reverse.return_value = None
        filled, _ = backfill_geocode([_record()], client=client)
        self.assertEqual(filled[0]["municipality"], "")
        self.assertEqual(filled[0]["province"], "")
        self.assertEqual(filled[0]["address"], "6F4Q67Q9+WQ7")

    def test_invalid_coordinates_are_skipped(self):
        for coords in ((0, 0), (None, 15.0), ("x", "y")):
            record = _record(latitude=coords[0], longitude=coords[1])
            filled, _ = backfill_geocode([record], client=MagicMock())
            self.assertEqual(filled[0]["address"], "")

    def test_preserves_previous_run_flags(self):
        record = _record(
            municipality="Luanda",
            municipality_inferred=True,
            province="Luanda",
            province_inferred=True,
        )
        filled, _ = backfill_geocode([record], client=None)
        self.assertTrue(filled[0]["municipality_inferred"])
        self.assertTrue(filled[0]["province_inferred"])

    def test_does_not_mutate_input(self):
        record = _record()
        backfill_geocode([record], client=None)
        self.assertEqual(record["address"], "")


class MergePrefersRealAddressTest(unittest.TestCase):
    def test_real_address_beats_plus_code_placeholder(self):
        winner = _record(
            latitude=-7.7602146,
            longitude=15.2694335,
            address="6F4Q67Q9+WQ7",
            address_source=ADDRESS_SOURCE_PLUS_CODE,
            source_type="operator_website",
            source_name="Sonangol",
        )
        loser = _record(
            latitude=-7.7602147,
            longitude=15.2694336,
            address="Rua Principal 123",
            source_type="openstreetmap",
            source_name="OSM",
        )
        merged = deduplicate_records([winner, loser])
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["address"], "Rua Principal 123")
        self.assertNotIn("address_source", merged[0])

    def test_plus_code_survives_when_no_real_address(self):
        winner = _record(
            address="6F4Q67Q9+WQ7",
            address_source=ADDRESS_SOURCE_PLUS_CODE,
            source_type="operator_website",
            source_name="Sonangol",
        )
        loser = _record(
            latitude=-7.7602147,
            longitude=15.2694336,
            source_type="openstreetmap",
            source_name="OSM",
        )
        merged = deduplicate_records([winner, loser])
        self.assertEqual(merged[0]["address"], "6F4Q67Q9+WQ7")
        self.assertEqual(merged[0]["address_source"], ADDRESS_SOURCE_PLUS_CODE)


if __name__ == "__main__":
    unittest.main()
