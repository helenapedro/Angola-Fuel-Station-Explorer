"""Tests for the Portuguese methodology page (PR 2)."""

import unittest

import dash

from map_dashboard.metodologia import (
    build_metodologia_layout,
    build_source_status_items,
    format_meta_summary_pt,
    translate_source_status,
)


def _collect_text(component):
    if isinstance(component, str):
        return component
    if isinstance(component, (list, tuple)):
        return " ".join(_collect_text(child) for child in component)
    children = getattr(component, "children", None)
    if children is None:
        return ""
    return _collect_text(children)


class MetodologiaTest(unittest.TestCase):
    def test_page_registers_at_metodologia(self):
        # register_page requires an app with use_pages=True, as in app.py.
        dash.Dash(__name__, use_pages=True, pages_folder="")
        import pages.metodologia  # noqa: F401  (registration side effect)

        paths = [page["path"] for page in dash.page_registry.values()]
        self.assertIn("/metodologia", paths)

    def test_layout_contains_governance_and_quality_policy(self):
        text = _collect_text(build_metodologia_layout())
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

    def test_layout_makes_no_positive_official_claim(self):
        text = _collect_text(build_metodologia_layout())
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

    def test_source_status_translation(self):
        self.assertEqual(translate_source_status("loaded"), "carregada")
        self.assertEqual(
            translate_source_status("stale_reused"),
            "reutilizada depois de uma falha",
        )
        self.assertEqual(translate_source_status("failed"), "falhou nesta recolha")
        meta = {
            "source_status": [
                {
                    "source": "OpenStreetMap",
                    "status": "stale_reused",
                    "record_count": 187,
                    "is_stale": True,
                }
            ]
        }
        text = _collect_text(build_source_status_items(meta))
        self.assertIn("OpenStreetMap", text)
        self.assertIn("reutilizada depois de uma falha", text)
        self.assertIn("desatualizada", text)


if __name__ == "__main__":
    unittest.main()
