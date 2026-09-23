# Geocoding backfill: addresses, municipalities, provinces from coordinates

## Problem

Every station has coordinates, but the location fields are sparse
(2026-09-23 snapshot, 279 stations):

- 129 without `address`
- 138 without `municipality`
- 144 without `province` (after the municipality→province table backfill)

Coordinates alone are enough to recover all three — no manual research,
no guessing.

## Approach

Two mechanisms, both deterministic, both "fill empty only, never
overwrite":

### 1. Plus codes for `address` — fully offline

A [plus code](https://maps.google.com/pluscodes/) (open location code)
is computable locally from latitude/longitude — no API, no cost, no
rate limits. It is a genuine, navigable address: paste it into Google
Maps and it resolves, which matters in areas without street names.

- Full 11-character code (`6F4Q67Q9+WQ7`, ~3 m precision) when no
  locality is known.
- Compound form (`67Q9+WQ7 Negage, Angola`) when the municipality is
  known — the first 4 characters are dropped and the locality name acts
  as the recovery reference, exactly the format Google Maps displays.

Filled addresses carry `"address_source": "plus_code"` so a real
street address arriving later from a source wins the dedup merge
(`_merge_into` prefers non-plus-code addresses).

### 2. Nominatim reverse geocoding for `municipality` / `province`

OpenStreetMap's Nominatim (`reverse`, `addressdetails=1`, `zoom=14`):

- `county`/`municipality` → municipality, with the `Município de/do/da`
  prefix stripped (`Município do Belas` → `Belas`).
- `state` → province, with ` Province`/` Província` suffix stripped.

Priority for municipality: `municipality` → `county` → `city` →
`town` → `village`. `suburb`/`road` are deliberately ignored (bairro
level, not municipality).

Why Nominatim and not a boundary polygons file: Angola's 2024 reform
(18 → 21 provinces) makes pre-2024 polygon datasets (e.g.
geoBoundaries, built from 2021 data with 18 provinces) stale, and
fetching OSM relations via Overpass is unreliable from automation.
Nominatim serves current OSM data — verified: Catete resolves to
`Icolo e Bengo Province`, a post-reform province.

### Precedence

1. Values already on the record (from any source) are never touched.
2. The curated municipality→province table (`ingestion/provinces.py`)
   runs first — explicit verified mappings outrank geocoding.
3. Nominatim fills whatever is still empty.
4. Plus codes fill empty addresses last, using the municipality
   (original or just backfilled) for the compound form.

Inferred values are flagged: `province_inferred` (existing),
`municipality_inferred` (new). Plus-code addresses are marked via
`address_source: "plus_code"` rather than an inference flag — the code
is computed from the coordinates, not guessed.

### Province naming

Nominatim returns post-reform names (`Icolo e Bengo`) and Portuguese
spellings (`Uíge`, `Malanje`, `Bié`, `Huíla`, `Cuanza Norte/Sul`).
A small normalization map aligns these with the dataset's existing
spellings (`Uige`, `Malange`, `Bie`, `Huila`, `Kwanza Norte/Sul`,
`Kuando Kubango`); genuinely new provinces (e.g. `Icolo e Bengo`) pass
through as named. Mixed 18/21-province values are a transitional
reality of the reform, not an error.

## Operational notes

- **Politeness**: max ~1 request/second, descriptive `User-Agent`
  (Nominatim usage policy). ~144 lookups ≈ 2–3 minutes on a cold run.
- **Cache**: `data/geocode_cache.json`, keyed by coordinates rounded
  to 4 decimals (~11 m). Committed to the repo so weekly refreshes are
  incremental and reproducible; the refresh workflow commits cache
  updates alongside the snapshots.
- **Failure mode**: any network/API failure returns `None` and the
  field stays empty. The pipeline never fails because geocoding
  failed. Plus-code addresses always succeed (offline).
- **Where the Nominatim run happens**: the ~144 sequential requests
  trip the sandbox network approval gate, so sandbox regenerations use
  `--no-geocode` (plus codes only). The full Nominatim run happens in
  the GitHub Actions refresh workflow, where network is unrestricted;
  the workflow commits `data/geocode_cache.json` alongside the
  snapshots, so later runs are incremental everywhere.
- **Offline mode** (`--offline`): plus codes still fill addresses;
  Nominatim is skipped.
- **Stale records**: re-enter the pipeline with their previous
  plus-code addresses and inferred flags intact
  (`setdefault` pattern, same as `backfill_province`).

## Contract

`tests/test_dataset_contract.py` asserts every clean station with
valid coordinates has a non-empty address — enforceable because plus
codes are offline and deterministic. Municipality/province coverage is
reported in snapshot metadata (`geocode_backfill`) but not hard-gated:
it depends on an external API.
