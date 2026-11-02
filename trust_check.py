"""Ready-for-trust verification for Phase 0 (PR 5).

This module implements the ``is_ready_for_trust`` check from the
Phase 0 design: it verifies the eight "ready for trust" criteria
against a metadata dict, a version registry list and the methodology
text, and reports which criteria fail. It adds no end-user
functionality and it never invents evidence: with the current
production snapshot (no ``confidence_counts``, no registry file) it
correctly reports "not ready". The dated live proofs (real ingestion
run, UI/API consistency check, stale-warning click test, methodology
review by the project owner) stay manual and are recorded outside
this module; this check verifies the mechanisms those proofs rely on.

Standard library only.
"""

BANNED_PHRASES = (
    "oficial",
    "validado pelo IRDP",
    "validado pelo operador",
    "endossado",
    "certificado",
    "homologado",
    "garantido",
)

_GOVERNANCE_PHRASES = (
    "Helena Pedro",
    "06:00",
    "portão de publicação",
    "7 dias",
)

CRITERIA = {
    1: "complete public metadata, including confidence_counts, and a matching version entry",
    2: "stale/overdue warning derivable from freshness for display next to the map",
    3: "corrections linkable to a snapshot (station id, version id, generated date)",
    4: "methodology in clear partner language, including what the project is not",
    5: "no terms implying official validation without a written agreement",
    6: "immutable version history with visible gaps",
    7: "refresh governance published (owner, cadence, publication gate, failure handling)",
    8: "UI and API metadata contract consistent for the same snapshot",
}


def _banned_found(text):
    lowered = (text or "").lower()
    return [phrase for phrase in BANNED_PHRASES if phrase in lowered]


def evaluate_ready_for_trust(meta, versions, methodology_text):
    """Return (ready, failed_criteria) for the eight criteria.

    ``meta`` is a metadata dict as returned by
    ``dataset_meta.load_dataset_meta`` (or ``None``). ``versions`` is
    the registry list from ``dataset_versions.load_dataset_versions``.
    ``methodology_text`` is the methodology page text. Criterion 3 is
    verified here through the snapshot fields a correction must cite
    (station id, version id, generated date); the link builder that
    carries them is verified directly by tests/test_reports.py.
    """
    failed = []

    # 1: complete metadata and a matching version entry.
    versions = versions or []
    meta_ok = (
        isinstance(meta, dict)
        and meta.get("generated_at")
        and meta.get("record_count") is not None
        and meta.get("rejected_count") is not None
        and isinstance(meta.get("source_status"), list)
        and isinstance(meta.get("confidence_counts"), dict)
        and sum(meta["confidence_counts"].values()) == meta["record_count"]
    )
    version_ok = bool(meta_ok) and any(
        v.get("version_id") == meta.get("version_id")
        and v.get("generated_at") == meta.get("generated_at")
        and v.get("record_count") == meta["record_count"]
        for v in versions
    )
    if not (meta_ok and version_ok):
        failed.append(1)

    # 2: freshness status is one of the four derived states, so the
    # badge can show fresh/stale/overdue/unavailable next to the map.
    if not (isinstance(meta, dict) and meta.get("freshness_status") in
            ("fresh", "stale", "overdue", "unavailable")):
        failed.append(2)

    # 3: a correction can be tied to a snapshot, because the
    # metadata and a matching version entry exist to cite. The link
    # builder that carries station id, version id and generated date
    # into the issue is verified by tests/test_reports.py.
    if not version_ok:
        failed.append(3)

    # 4: methodology states what the project is not, in plain language.
    text = methodology_text or ""
    if "O que o projeto não é" not in text or "Política de qualidade do dado" not in text:
        failed.append(4)

    # 5: no banned official-validation terms in the methodology text.
    if _banned_found(text):
        failed.append(5)

    # 6: version history has no duplicate version ids and is ordered
    # by generation date, so gaps stay visible and nothing is rewritten.
    version_ids = [v.get("version_id") for v in versions]
    generated_dates = [v.get("generated_at") for v in versions]
    if len(version_ids) != len(set(version_ids)) or generated_dates != sorted(generated_dates):
        failed.append(6)
    if not versions:
        failed.append(6)

    # 7: governance published on the methodology page.
    if any(phrase not in text for phrase in _GOVERNANCE_PHRASES):
        failed.append(7)

    # 8: consistency is a property of the shared function, verified
    # by tests that call the badge formatter and the API with the
    # same fixture. Here, check the contract fields exist on both
    # sides of the inputs: the metadata carries the fields the badge
    # and the endpoint both render.
    if not (
        isinstance(meta, dict)
        and meta.get("version_id")
        and meta.get("snapshot_origin")
        and meta.get("freshness_status")
    ):
        failed.append(8)

    return (not failed, failed)


def is_ready_for_trust(meta, versions, methodology_text):
    """Return True only when all eight criteria pass."""
    ready, _failed = evaluate_ready_for_trust(meta, versions, methodology_text)
    return ready
