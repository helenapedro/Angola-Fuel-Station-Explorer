"""Branding: logo assets exist and the share image is in the meta tags.

Uses only stdlib plus ``seo.py``, so this runs in the CI environment
too, like the other source-text checks.
"""

import unittest
from pathlib import Path

from seo import SITE_IMAGE, SITE_URL, build_meta_tags

REPO = Path(__file__).resolve().parents[1]


class BrandingTest(unittest.TestCase):
    def test_logo_assets_exist(self):
        self.assertTrue((REPO / "assets" / "logo.png").is_file())
        self.assertTrue((REPO / "assets" / "favicon.ico").is_file())

    def test_share_image_in_meta_tags(self):
        self.assertEqual(SITE_IMAGE, f"{SITE_URL}/assets/logo.png")
        tags = build_meta_tags()
        by_key = {(t.get("property") or t.get("name")): t["content"] for t in tags}
        self.assertEqual(by_key["og:image"], SITE_IMAGE)
        self.assertEqual(by_key["twitter:image"], SITE_IMAGE)


if __name__ == "__main__":
    unittest.main()
