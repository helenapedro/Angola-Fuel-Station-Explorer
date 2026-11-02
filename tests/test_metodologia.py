"""Tests for the Portuguese methodology page (PR 2).

CI installs only the non-Dash test dependencies, so no test in this
file may import Dash or any module that imports Dash. The methodology
content is therefore checked in two Dash-free ways: the pure helpers
in ``map_dashboard/metodologia_content.py`` are imported and tested
directly, and the rendering module's literal text is read from its
source file and checked for required and banned phrases. The page
registration is checked the same way, by reading
``pages/metodologia.py``. A real browser check remains the proof that
the page actually renders; these tests only prove the content and
helpers are correct.
"""

import unittest
from pathlib import Path

from map_dashboard.metodologia_content import (
    format_meta_summary_pt,
    overdue_note_pt,
    source_status_lines,
    translate_source_name,
    translate_source_status,
    version_lines,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


class MetodologiaTest(unittest.TestCase):
    def test_page_registers_at_metodologia(self):
        page_source = (REPO_ROOT / "pages" / "metodologia.py").read_text(encoding="utf-8")
        self.assertIn('path="/metodologia"', page_source)
        self.assertIn("register_page", page_source)

    def test_rendering_source_contains_governance_and_quality_policy(self):
        text = (REPO_ROOT / "map_dashboard" / "metodologia.py").read_text(encoding="utf-8")
        for required in (
            "Helena Pedro",
            "06:00",
            "Política de qualidade do dado",
            "base_publica_osm",
            "operador_via_osm",
            "confirmado_pelo_operador",
            "O que o projeto não é",
            "Como reportar um erro",
            "14 dias",
        ):
            self.assertIn(required, text)

    def test_rendering_source_makes_no_positive_official_claim(self):
        text = (REPO_ROOT / "map_dashboard" / "metodologia.py").read_text(encoding="utf-8")
        for banned in (
            "oficial",
            "validado pelo IRDP",
            "validado pelo operador",
            "endossado",
            "certificado",
            "homologado",
            "garantido",
        ):
            self.assertNotIn(banned, text)

    def test_no_test_or_content_module_imports_dash(self):
        for path in (
            REPO_ROOT / "tests" / "test_metodologia.py",
            REPO_ROOT / "map_dashboard" / "metodologia_content.py",
        ):
            lines = path.read_text(encoding="utf-8").splitlines()
            imports = [
                line.strip()
                for line in lines
                if line.strip().startswith("import dash")
                or line.strip().startswith("from dash")
            ]
            self.assertEqual(imports, [])

    def test_meta_summary_pt(self):
        self.assertEqual(
            format_meta_summary_pt(None),
            "Data de atualização indisponível.",
        )
        fresh = {
            "generated_at": "2026-10-28T00:00:00+00:00",
            "age_days": 0,
            "freshness_status": "fresh",
            "record_count": 279,
        }
        self.assertEqual(
            format_meta_summary_pt(fresh),
            "Snapshot de 28/10/2026 (há 0 dias), com 279 registos. Estado de frescura: atualizado.",
        )
        overdue = {
            "generated_at": "2026-09-23T11:27:12+00:00",
            "age_days": 35,
            "freshness_status": "overdue",
            "record_count": 279,
        }
        self.assertIn("em atraso", format_meta_summary_pt(overdue))

    def test_rendering_source_avoids_unexplained_jargon(self):
        # Proof 4 follow-up: partner language, no unexplained
        # developer terms. /api/v1/meta stays as the evidence link.
        text = (REPO_ROOT / "map_dashboard" / "metodologia.py").read_text(encoding="utf-8")
        for jargon in (
            "generated_at",
            "dyno",
            "GitHub Actions",
            "ficheiro JSON",
            "cache de 300 segundos",
            "portão de publicação",
            "tria correções",
            "Abrir uma issue",
            "adaptador",
            "BundledLegacyPumangol",
            "acordo de nível de serviço",
            "coordenadas (0, 0)",
            "artefactos de texto",
            "nome normalizado",
        ):
            self.assertNotIn(jargon, text)
        for plain in (
            "um único servidor",
            "ficheiro de dados válido",
            "pedido público de correção",
            "Está previsto um formulário sem conta",
        ):
            self.assertIn(plain, text)

    def test_quality_levels_highlighted_at_top_with_anchor(self):
        text = (REPO_ROOT / "map_dashboard" / "metodologia.py").read_text(encoding="utf-8")
        highlight = text.index("Níveis de qualidade, em resumo")
        self.assertLess(highlight, text.index("O que o projeto é"))
        for level in ("base_publica_osm", "operador_via_osm", "confirmado_pelo_operador"):
            self.assertIn(level, text[highlight : highlight + 1500])
        self.assertIn('href="#niveis-de-qualidade"', text)
        self.assertIn('section_id="niveis-de-qualidade"', text)

    def test_source_status_translation(self):
        self.assertEqual(
            translate_source_name("BundledLegacyPumangol"),
            "Snapshot anterior da Pumangol",
        )
        self.assertEqual(translate_source_name("Pumangol"), "Pumangol")
        self.assertEqual(translate_source_status("loaded"), "carregada")
        self.assertEqual(
            translate_source_status("stale_reused"),
            "reutilizada depois de uma falha",
        )
        self.assertEqual(translate_source_status("failed"), "falhou nesta recolha")
        lines = source_status_lines(
            {
                "source_status": [
                    {
                        "source": "OpenStreetMap",
                        "status": "stale_reused",
                        "record_count": 187,
                        "is_stale": True,
                    }
                ]
            }
        )
        self.assertEqual(len(lines), 1)
        self.assertIn("OpenStreetMap", lines[0])
        self.assertIn("reutilizada depois de uma falha", lines[0])
        self.assertIn("desatualizada", lines[0])
        legacy = source_status_lines(
            {
                "source_status": [
                    {
                        "source": "BundledLegacyPumangol",
                        "status": "loaded",
                        "record_count": 80,
                        "is_stale": False,
                    }
                ]
            }
        )
        self.assertIn("Snapshot anterior da Pumangol", legacy[0])
        self.assertNotIn("BundledLegacyPumangol", legacy[0])

    def test_version_lines_describe_each_version(self):
        lines = version_lines(
            [
                {
                    "version_id": "2026-09-23T11:27:12+00:00",
                    "generated_at": "2026-09-23T11:27:12+00:00",
                    "record_count": 279,
                    "rejected_count": 63,
                    "freshness_status_at_publication": "fresh",
                }
            ]
        )
        self.assertEqual(len(lines), 1)
        self.assertIn("23/09/2026", lines[0])
        self.assertIn("279 registos", lines[0])

    def test_overdue_note_only_when_overdue_and_states_no_invented_cause(self):
        overdue = {
            "generated_at": "2026-09-23T11:27:12+00:00",
            "age_days": 39,
            "freshness_status": "overdue",
        }
        note = overdue_note_pt(overdue)
        self.assertIsNotNone(note)
        self.assertIn("28 dias", note)
        fresh = dict(overdue, freshness_status="fresh", age_days=3)
        self.assertIsNone(overdue_note_pt(fresh))
        self.assertIsNone(overdue_note_pt(None))

    def test_rendering_source_contains_versions_section_and_osm_attribution(self):
        text = (REPO_ROOT / "map_dashboard" / "metodologia.py").read_text(encoding="utf-8")
        self.assertIn("Histórico de versões", text)
        self.assertIn("metodologia-versions", text)
        self.assertIn("OpenStreetMap contributors", text)
        self.assertIn("Open Database License", text)
        page_source = (REPO_ROOT / "pages" / "metodologia.py").read_text(encoding="utf-8")
        self.assertIn("metodologia-versions", page_source)
        self.assertIn("metodologia-overdue-note", page_source)


if __name__ == "__main__":
    unittest.main()
