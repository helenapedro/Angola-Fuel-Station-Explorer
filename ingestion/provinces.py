"""Municipality -> province backfill for Angola.

OSM records often carry ``addr:city``/``addr:municipality`` but no
``addr:province`` (204 of 279 records lacked province in the 2026-09-23
snapshot). This module fills the gap deterministically from an explicit
table of observed, unambiguous municipalities — the same data-as-code
philosophy as the operator registry: never guess, leave unknown values
empty.

Administrative-division note: the table follows the division used by the
dataset (18 provinces, with the dataset's spellings such as "Malange" and
"Kuando Kubango"). Municipalities affected by Angola's 2024 reform
(18 -> 21 provinces, e.g. Funda) are deliberately excluded until their
current province is verified. Neighborhood names sometimes misfiled as
municipality (e.g. "Bairro da Luz") are excluded too.
"""

PROVINCE_BACKFILL_VERSION = 1

# Normalized municipality -> province. Keys must already be normalized
# with _normalize_municipality(); only unambiguous, verified mappings.
_MUNICIPALITY_TO_PROVINCE = {
    "luanda": "Luanda",
    "lubango": "Huila",  # capital of Huila
    "quibala": "Kwanza Sul",
    "benguela": "Benguela",
    "huambo": "Huambo",
    "ondjiva": "Cunene",  # capital of Cunene
    "malanje": "Malange",  # dataset spelling
    "panguila": "Bengo",
    "waku kungo": "Kwanza Sul",
    "moçâmedes": "Namibe",  # capital of Namibe
    "xangongo": "Cunene",
    "chongoroi": "Benguela",
    "canjala": "Benguela",
    "catengue": "Benguela",
    "chinjenje": "Huambo",
}


def _normalize_municipality(value):
    return " ".join(str(value or "").casefold().split())


def backfill_province(record):
    """Fill the record's province from its municipality when possible.

    Returns ``(record, filled)``: a copy of the record (province filled
    only when the record had none and its municipality maps
    unambiguously — tagged provinces are never overwritten) and whether
    the province was inferred. Callers store the flag as
    ``province_inferred`` so backfilled values stay auditable.
    """
    if record.get("province"):
        filled = dict(record)
        # Preserve a previous run's flag: stale records re-enter the
        # pipeline and must keep their inferred provenance.
        filled.setdefault("province_inferred", False)
        return filled, False
    province = _MUNICIPALITY_TO_PROVINCE.get(
        _normalize_municipality(record.get("municipality"))
    )
    filled = dict(record)
    if province:
        filled["province"] = province
        filled["province_inferred"] = True
        return filled, True
    filled["province_inferred"] = False
    return filled, False


def count_backfilled(records):
    """How many records in `records` carry an inferred province."""
    return sum(1 for record in records if record.get("province_inferred"))
