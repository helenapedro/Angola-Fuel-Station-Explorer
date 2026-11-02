"""Navigation rules: Metodologia lives in the footer only, no portfolio link in the footer.

Source-text checks, like tests/test_metodologia.py, because CI does not
install Dash and cannot build the layout.
"""

import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


class NavigationTest(unittest.TestCase):
    def test_metodologia_link_only_in_footer(self):
        app_source = (REPO / "app.py").read_text(encoding="utf-8")
        layout_source = (REPO / "map_dashboard" / "layout.py").read_text(encoding="utf-8")
        self.assertEqual(app_source.count('href="/metodologia"'), 1)
        self.assertNotIn("NavLink", app_source)
        footer_start = app_source.index("footer = ")
        self.assertGreater(app_source.index('href="/metodologia"'), footer_start)
        self.assertNotIn("/metodologia", layout_source)

    def test_footer_has_no_portfolio_link(self):
        app_source = (REPO / "app.py").read_text(encoding="utf-8")
        self.assertNotIn("helenapedro.github.io", app_source)

    def test_dashboard_ui_is_portuguese(self):
        layout_source = (REPO / "map_dashboard" / "layout.py").read_text(encoding="utf-8")
        for phrase in ["Filtros", "Todas as marcas", "Postos", "Marcas", "Províncias", "Municípios"]:
            self.assertIn(phrase, layout_source)
        for phrase in ["Station Finder", "All brands", "Stations", "Brands", "Provinces", "Municipalities"]:
            self.assertNotIn(phrase, layout_source)


if __name__ == "__main__":
    unittest.main()
