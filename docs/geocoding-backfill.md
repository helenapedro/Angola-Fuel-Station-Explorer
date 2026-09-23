# Geocoding backfill: addresses from coordinates, fully offline

## Problem

Every station has coordinates, but the location fields are sparse
(2026-09-23 snapshot, 279 stations):

- 129 without `address`
- 138 without `municipality`
- 144 without `province` (after the municipality→province table backfill)

Coordinates alone are enough to recover addresses — no manual research,
no guessing.

## Approach

Two mechanisms, both deterministic, both "fill empty only, never
overwrite", both **fully offline** (no network calls of any kind):

### 1. Plus codes for `address`

A [plus code](https://maps.google.com/pluscodes/) (open location code)
is computable locally from latitude/longitude — pure math via the
`openlocationcode` library: no API, no cost, no rate limits, no
approval gates. It is a genuine, navigable address: paste the bare
full code (e.g. `6F4Q67Q9+WQ7`) into Google Maps and it resolves,
which matters in areas without street names.

- Full 11-character code (`6F4Q67Q9+WQ7`, ~3 m precision), always.
  The compound form (`67Q9+WQ7 Negage, Angola`) was considered but
  dropped: the locality suffix requires reverse geocoding, which this
  design excludes.

Filled addresses carry `"address_source": "plus_code"` so a real
street address arriving later from a source wins the dedup merge
(`_merge_into` prefers non-plus-code addresses).

### 2. Explicit municipality→province table for `province`

`ingestion/provinces.py` holds a curated table of observed,
unambiguous municipalities (same data-as-code philosophy as the
operator registry). It runs before the address backfill and fills
provinces for stations that have a municipality but no province.
Verified additions 2026-09-23: `Caconda` → Huíla, `Alto Hama` →
Huambo.

Municipalities have **no** offline backfill source: without reverse
geocoding there is no way to derive a municipality from coordinates
alone, so stations without one keep it empty — honestly, like
`Unknown` operators.

### Why not reverse geocoding or a boundary spatial join

- **Nominatim / any per-coordinate online lookup**: dropped at
  Helena's direction. ~144 sequential requests trip the sandbox
  network approval gate ("may include personal information" card on
  every batch) even though the coordinates are public station data,
  not user location. Offline is also deterministic, has no rate
  limits, and never fails on flaky network.
- **Spatial join against GADM/geoBoundaries polygons**: considered
  and rejected. Those datasets predate Angola's 2024 reform (18
  provinces) and would mislabel post-reform areas — the same reason
  the pipeline treats 2024-reform municipalities as unverified until
  confirmed. No post-reform offline boundary dataset was available.

### Precedence

1. Values already on the record (from any source) are never touched.
2. The curated municipality→province table (`ingestion/provinces.py`)
   fills empty provinces from known municipalities.
3. Plus codes fill empty addresses from coordinates.

Inferred provinces are flagged `province_inferred` (existing).
Plus-code addresses are marked via `address_source: "plus_code"`
rather than an inference flag — the code is computed from the
coordinates, not guessed.

## Operational notes

- **Zero network**: the geocoding step makes no HTTP requests. It runs
  identically in the sandbox, CI, and GitHub Actions; no flags, no
  cache file, no approval cards.
- **Stale records**: re-enter the pipeline with their previous
  plus-code addresses intact; fill-empty-only means regeneration is
  idempotent.

## Contract

`tests/test_dataset_contract.py` asserts every clean station with
valid coordinates has a non-empty address — enforceable because plus
codes are offline and deterministic. Province coverage is reported in
snapshot metadata (`province_backfill`) but not hard-gated.
