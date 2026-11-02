"""SEO helpers for the Angola Fuel Station Explorer."""

from datetime import date

SITE_URL = "https://gaspump.hmpedro.com"
SITE_TITLE = "Postos de Combustível em Angola | Angola Fuel Station Explorer"
SITE_DESCRIPTION = (
    "Encontra postos de combustível em Angola por província, município, marca e nome do posto "
    "com um mapa interativo de postos de combustível."
)
SITE_KEYWORDS = (
    "postos de combustível em Angola, postos de gasolina Angola, mapa de postos de combustível Angola, "
    "postos de combustível Luanda, localizador de postos Angola"
)


def build_meta_tags():
    return [
        {"name": "viewport", "content": "width=device-width, initial-scale=1"},
        {"name": "description", "content": SITE_DESCRIPTION},
        {"name": "keywords", "content": SITE_KEYWORDS},
        {"property": "og:type", "content": "website"},
        {"property": "og:title", "content": SITE_TITLE},
        {"property": "og:description", "content": SITE_DESCRIPTION},
        {"property": "og:url", "content": SITE_URL},
        {"name": "twitter:card", "content": "summary_large_image"},
        {"name": "twitter:title", "content": SITE_TITLE},
        {"name": "twitter:description", "content": SITE_DESCRIPTION},
    ]


def build_robots_txt():
    return f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n"


def build_sitemap_xml():
    lastmod = date.today().isoformat()
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        "<url>"
        f"<loc>{SITE_URL}/</loc>"
        f"<lastmod>{lastmod}</lastmod>"
        "<changefreq>weekly</changefreq>"
        "<priority>1.0</priority>"
        "</url>"
        "</urlset>"
    )
