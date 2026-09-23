"""Verified operator registry for Angola fuel retail.

Angola's fuel-station market was historically an oligopoly of four retail
brands (researched 2026-09-23; see docs/data-quality.md). Etu Energias
(formerly Somoil, rebranded ~2022) has since entered retail with its own
branded stations (e.g. Posto de Abastecimento Cuca, Luanda, opened Dec 2025).
Raw operator strings from OpenStreetMap tags and legacy snapshots are mapped
deterministically against this registry instead of being guessed at.

Design notes:
- Data-as-code on purpose: explicit, versioned, reviewable, and it adds
  no new dependency (no YAML/JSON loader needed).
- Matching is exact/prefix on normalized strings — never fuzzy — so the
  pipeline behaves identically on every run.
- "Etu" alone is NOT an alias: it means "us/ours" in Bantu languages and
  appears in ordinary station names, so it would cause false positives in
  name-based inference. Only the full "Etu Energias" (and the legacy
  "Somoil") map to the brand.
"""

UNKNOWN_OPERATOR = "Unknown"

# Canonical retail brands, verified against public sources (2026-09-23,
# Etu Energias added 2026-09-23).
CANONICAL_OPERATORS = (
    "Sonangol",  # state-owned; largest network
    "Pumangol",  # 80+ stations; wholly owned by Sonangol since Dec 2021
    "TotalEnergies",  # in Angola since 1953; stations with Sonangol
    "Sonangalp",  # JV Galp (49%) / Sonangol (51%), since 1994
    "Etu Energias",  # private; ex-Somoil (rebrand ~2022); own-brand retail
)

# Normalized alias -> canonical brand. Keys must already be normalized
# with _normalize_alias(); keep every observed variant listed explicitly.
OPERATOR_ALIASES = {
    "sonangol": "Sonangol",
    "sonagol": "Sonangol",  # typo observed in OSM tags
    "sonangola": "Sonangol",  # colloquial variant observed in OSM names
    "pumangol": "Pumangol",
    "pumangola": "Pumangol",  # colloquial variant observed in OSM names
    "puma": "Pumangol",
    "puma energy": "Pumangol",
    "totalenergies": "TotalEnergies",
    "total": "TotalEnergies",
    "totalenergies marketing & services angola, s.a.": "TotalEnergies",
    "totalenergies marketing angola": "TotalEnergies",
    "sonangalp": "Sonangalp",
    "sonagalp": "Sonangalp",  # typo observed in OSM tags
    "galp": "Sonangalp",  # Galp retails in Angola only via the Sonangalp JV
    "etu energias": "Etu Energias",
    "somoil": "Etu Energias",  # legacy name before the ~2022 rebrand
}

_LEGAL_SUFFIXES = ("lda", "s.a.", "sa", "limitada")


def _normalize_alias(value):
    text = " ".join(str(value or "").casefold().split())
    for suffix in _LEGAL_SUFFIXES:
        if text.endswith(" " + suffix):
            text = text[: -(len(suffix) + 1)].rstrip()
            break
    return text.strip(" .,")


def canonicalize_operator(raw_operator, station_name=""):
    """Map a raw operator string to a verified brand or "Unknown".

    Never invents a brand: anything outside the registry stays "Unknown"
    so the station is kept but honestly labeled.
    """
    candidate = _normalize_alias(raw_operator)
    if candidate in OPERATOR_ALIASES:
        return OPERATOR_ALIASES[candidate]

    # "totalenergies marketing & services angola, s.a." -> TotalEnergies
    for alias, canonical in sorted(OPERATOR_ALIASES.items(), key=lambda item: -len(item[0])):
        if candidate.startswith(alias + " ") or candidate.startswith(alias + ","):
            return canonical

    # Fall back to the station name only when the operator tag is missing:
    # "TotalEnergies - P.A. BOA ENTRADA" -> TotalEnergies.
    if not candidate or candidate == UNKNOWN_OPERATOR.casefold():
        for token in _normalize_alias(station_name).split(" "):
            if token in OPERATOR_ALIASES:
                return OPERATOR_ALIASES[token]

    return UNKNOWN_OPERATOR


def canonicalize_record(record):
    """Return a copy of the record with the operator canonicalized."""
    canonical_record = dict(record)
    canonical_record["operator"] = canonicalize_operator(
        record.get("operator"), record.get("station")
    )
    return canonical_record
