"""Ready-for-trust verification (PR 5, design section 6).

These tests verify the mechanisms behind the eight criteria, using
fixtures, and verify that the check itself reports "not ready" for
the current production snapshot shape (no confidence_counts, no
registry file). They do not claim the live proofs: the dated
ingestion run, the live UI/API consistency check, the stale-warning
click test and the owner's methodology review stay manual and must
be recorded with dated evidence before any partner presentation.
"""

import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

import dataset_meta
import dataset_versions
import reports
from api.deps import get_station_data
from api.main import app
from dataset_meta import format_dataset_badge
from reports import Report, build_issue_url
from trust_check import evaluate_ready_for_trust, is_ready_for_trust

REPO_ROOT = Path(__file__).resolve().parent.parent

META = {
    "version_id": "2026-10-05T06:00:00+00:00",
    "snapshot_origin": "helenapedro/Angola-Fuel-Station-Explorer:data/stations_clean.json",
    "generated_at": "2026-10-05T06:00:00+00:00",
    "record_count": 279,
    "rejected_count": 63,
    "source_status": [
        {"source": "OpenStreetMap", "status": "loaded", "record_count": 187, "is_stale": False}
    ],
    "confidence_counts": {
        "confirmado_pelo_operador": 0,
        "operador_via_osm": 81,
        "base_publica_osm": 198,
    },
    "freshness_status": "fresh",
    "is_stale": False,
    "age_days": 0,
    "fresh": True,
}

VERSIONS = [
    {
        "version_id": "2026-10-05T06:00:00+00:00",
        "snapshot_origin": "helenapedro/Angola-Fuel-Station-Explorer:data/stations_clean.json",
        "generated_at": "2026-10-05T06:00:00+00:00",
        "record_count": 279,
        "rejected_count": 63,
        "freshness_status_at_publication": "fresh",
        "source_status_summary": [],
    }
]

METHODOLOGY_TEXT = (
    "O que o projeto não é. Política de qualidade do dado. "
    "Responsável pelo dataset: Helena Pedro, única responsável. "
    "Cadência prevista: recolha semanal automática, às segundas-feiras, às 06:00. "
    "Antes de uma nova versão ser publicada, tem de passar numa verificação. "
    "A responsável revê uma falha da automação no prazo de 7 dias de calendário."
)


class ReadyForTrustTest(unittest.TestCase):
    def test_complete_fixture_is_ready(self):
        ready, failed = evaluate_ready_for_trust(META, VERSIONS, METHODOLOGY_TEXT)
        self.assertTrue(ready)
        self.assertEqual(failed, [])

    def test_current_snapshot_shape_is_not_ready(self):
        current = dict(META, confidence_counts=None, freshness_status="overdue",
                       age_days=39, fresh=False, is_stale=True)
        ready, failed = evaluate_ready_for_trust(current, [], METHODOLOGY_TEXT)
        self.assertFalse(ready)
        self.assertIn(1, failed)
        self.assertIn(3, failed)
        self.assertIn(6, failed)
        self.assertNotIn(2, failed)
        self.assertNotIn(4, failed)
        self.assertNotIn(5, failed)
        self.assertNotIn(7, failed)

    def test_confidence_counts_must_sum_to_record_count(self):
        bad = dict(META, confidence_counts={"confirmado_pelo_operador": 1})
        ready, failed = evaluate_ready_for_trust(bad, VERSIONS, METHODOLOGY_TEXT)
        self.assertFalse(ready)
        self.assertIn(1, failed)

    def test_banned_terms_fail_criterion_5(self):
        ready, failed = evaluate_ready_for_trust(
            META, VERSIONS, METHODOLOGY_TEXT + " Este projeto é oficial."
        )
        self.assertFalse(ready)
        self.assertIn(5, failed)

    def test_duplicate_version_ids_fail_criterion_6(self):
        ready, failed = evaluate_ready_for_trust(
            META, VERSIONS + VERSIONS, METHODOLOGY_TEXT
        )
        self.assertFalse(ready)
        self.assertIn(6, failed)

    def test_correction_link_carries_snapshot_fields(self):
        url = build_issue_url(
            Report(station_id=82879636726257, problem_type="morada_errada", details="", source_url=""),
            {"station": "KEU", "operator": "Unknown", "municipality": "", "province": "",
             "address": "6F6JC5RQ+VQM", "latitude": -5.5577802, "longitude": 12.1894286},
            "2026-09-23T11:27:12+00:00",
            "2026-09-23T11:27:12+00:00",
        )
        self.assertIn("82879636726257", url)
        self.assertIn("2026-09-23T11", url)
        self.assertIn("morada_errada", url)

    def test_badge_and_api_agree_on_the_same_fixture(self):
        # generated_at is "now", so the badge and the API, both reading
        # the same file through the same function, must agree.
        from datetime import datetime, timezone

        now_iso = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        fixture = {
            "generated_at": now_iso,
            "record_count": 279,
            "rejected_count": 63,
            "source_status": [],
            "confidence_counts": {
                "confirmado_pelo_operador": 0,
                "operador_via_osm": 81,
                "base_publica_osm": 198,
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "stations_clean.json"
            path.write_text(json.dumps({"metadata": fixture}, indent=2), encoding="utf-8")
            original = dataset_meta.CLEAN_DATA_PATH
            dataset_meta.CLEAN_DATA_PATH = path
            dataset_meta.clear_dataset_meta_cache()
            try:
                meta = dataset_meta.load_dataset_meta()
                badge = format_dataset_badge(meta)
                app.dependency_overrides[get_station_data] = (
                    lambda: (pd.DataFrame([{"id": 1}]), "live")
                )
                client = TestClient(app)
                body = client.get("/api/v1/meta").json()
            finally:
                dataset_meta.CLEAN_DATA_PATH = original
                dataset_meta.clear_dataset_meta_cache()
                app.dependency_overrides.clear()
        self.assertEqual(body["generated_at"], meta["generated_at"])
        self.assertEqual(body["freshness_status"], meta["freshness_status"])
        self.assertEqual(body["age_days"], meta["age_days"])
        self.assertEqual(body["confidence_counts"], fixture["confidence_counts"])
        badge_text = badge[0] if isinstance(badge, tuple) else badge
        self.assertIn(datetime.now(timezone.utc).strftime("%d/%m/%Y"), badge_text)

    def test_architecture_doc_exists_and_names_the_boundaries(self):
        text = (REPO_ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")
        for required in (
            "gunicorn",
            "PrefixRouter",
            "dataset_meta",
            "dataset_versions",
            "publication gate",
            "ephemeral",
            "No database serves requests",
        ):
            self.assertIn(required, text)
        self.assertNotIn("oficial", text.lower())

    def test_no_banned_claims_in_public_text(self):
        corpus = ""
        for rel in (
            "README.md",
            "map_dashboard/metodologia.py",
            "map_dashboard/layout.py",
            "map_dashboard/presentation.py",
            "seo.py",
            "docs/architecture.md",
        ):
            corpus += (REPO_ROOT / rel).read_text(encoding="utf-8") + "\n"
        lowered = corpus.lower()
        for banned in ("validado pelo irdp", "validado pelo operador", "endossado",
                       "certificado", "homologado"):
            self.assertNotIn(banned, lowered)
