# Design: data-quality gates in ingestion

## 1. Context

This work implements the data-quality item of the Overall assessment
(senior review, 2026-09-23). After PR #4 switched the serving layer to
the bundled `data/stations_clean.json` snapshot, production served 418
stations — but spot checks showed the snapshot is not trustworthy.

Measured on the 2026-09-22 snapshot (418 records):

| # | Finding | Count |
|---|---------|-------|
| 1 | Record pairs < 150 m apart (same physical station ingested twice) | 110 pairs |
| 2 | Station names that are raw OSM element ids (`way/954638665`) | dozens |
| 3 | Records with operator `Unknown` (OSM nodes without brand tags) | 179 (43%) |
| 4 | Brand spellings for the same company (`Pumangol`/`Puma`/`Puma Energy`/`PUMANGOL`/`pumangol`, `Sonagol`, `Sonagalp` typos) | 5+ variants |

Root cause: the pipeline merges three sources (generic OSM, Sonangol-filtered
OSM, legacy snapshot) but dedupes only on exact
`(operator, station name, rounded coordinates)` keys. The same station
arrives as `("Sonangol", "Sonangol", …)` from one source and
`("Unknown", "way/954638665", …)` from another — different keys, both
survive — and brand strings are never normalized.

## 2. Goals / non-goals

Goals:

- No obvious garbage on the map or API: no OSM ids as station names, no
  blatant duplicates, one spelling per brand.
- Deterministic, auditable rules — no fuzzy guessing, no ML.
- Quality enforced at **write time** (ingestion), so the weekly refresh
  keeps the snapshot clean and every consumer (dashboard, API) inherits it.
- Every dropped/merged record traceable (`stations_rejected.json`,
  `merged_sources`).

Non-goals:

- Manual curation of 418 stations; perfect ground truth (OSM data for
  Angola will never be perfect).
- Dropping `Unknown`-brand stations (a real fuel stop with unknown brand
  is still useful; the label is honest).
- Changing the serving layer (`station_data`, API, dashboard) — it
  already handles canonical columns and `None`s.

## 3. Design

### 3.1 Verified operator registry (new: `ingestion/operators.py`)

Angola's fuel retail was historically an oligopoly of four brands
(researched 2026-09-23), since joined by a fifth:

| Brand | Notes |
|---|---|
| Sonangol | State-owned; largest network |
| Pumangol | 80+ stations; wholly owned by Sonangol since Dec 2021 (ex-Puma Energy JV) |
| TotalEnergies | Present since 1953; stations in partnership with Sonangol |
| Sonangalp | JV Galp (49%) / Sonangol (51%), since 1994 |
| Etu Energias | Private; formerly Somoil (rebranded ~2022); own-brand retail stations operating (e.g. Posto Cuca, Luanda, opened Dec 2025) |

Sector context (2026-09-23): outside these brands, private supply comes
from **"bandeira branca"** (white-flag) independents — small private agents
selling unbranded fuel — and from independent dealers under models such as
**COFO** (company-owned, franchise-operated). Neither is a *brand*:
"bandeira branca" is the absence of one and COFO is an operating model
(a COFO station still flies a brand flag), so neither gets a registry
entry. Stations in these categories surface as `Unknown` (see 3.5).

OSM tag semantics: `brand` is the marketed flag on the station (what the
consumer sees); `operator` is often the local franchisee/dealer. The
ingestion record's `operator` field models the brand, so `normalize.py`
prefers the `brand` tag over `operator` — e.g. `brand=TotalEnergies` with
`operator="P.A. Kindombele"` canonicalizes to TotalEnergies.

The registry is data-as-code (no new dependency):

- `CANONICAL_OPERATORS`: the four verified brands.
- `OPERATOR_ALIASES`: explicit normalized-alias → canonical map, covering
  every variant observed in the data (`puma`, `puma energy`, `pumangol`,
  `sonagol` typo, `sonagalp` typo, `totalenergies marketing & services
  angola, s.a.`, …).

`canonicalize_operator(raw, station_name="")`:

1. Normalize the raw string (casefold, collapse whitespace, strip legal
   suffixes like `Lda`/`S.A.`), look it up in the alias table.
2. Prefix match: normalized input starting with a known alias
   (`"totalenergies marketing …"` → TotalEnergies).
3. Name inference, only when the operator tag is missing/`Unknown`: if a
   token of the station name matches the registry
   (`"TotalEnergies - P.A. BOA ENTRADA"` → TotalEnergies).
4. Otherwise `Unknown` — the station is kept, honestly labeled.

### 3.2 Spatial dedupe with merge (replaces exact-key dedupe)

`deduplicate_records` now clusters by proximity instead of exact keys:

- Two records within **150 m** are the same station, **unless both carry
  different verified (non-`Unknown`) operators** — competing brands can
  sit across the street from each other, and that must never merge.
- Records are considered best-first using the existing `_record_priority`
  (freshness, source rank, real name, address); the winner absorbs the
  loser.
- Merge fills gaps: an OSM-id station name or `Unknown` operator on the
  winner is replaced by the loser's real values; empty
  address/municipality/province are backfilled.
- Every surviving record carries `merged_sources`: the sorted list of
  distinct `source_name`s that confirm it (length ≥ 1).

Why 150 m: OSM node-vs-way-center offsets for the same site are typically
tens of meters; 150 m is conservative enough to avoid merging genuinely
distinct same-brand sites while catching the observed duplicates.

### 3.3 Name hygiene

After merging, any surviving record whose station name is still an OSM
element id (`^(node|way|relation)/\d+$`) is rejected with reason
`"station name is an OSM element id"`. Because merging runs first, only
truly unnamed stations are dropped — duplicates of branded stations are
absorbed, not lost.

### 3.4 Pipeline order

```
fetch (all sources)
  → canonicalize operators (registry)
  → validate (coordinates, required fields) → rejected
  → spatial dedupe + merge
  → name hygiene → rejected
  → write stations_clean.json / stations_rejected.json
```

All inside `split_valid_records`, so `sync_stations --offline --check`
(CI) exercises the full gate chain.

### 3.5 `Unknown`-brand policy (decision 2026-09-23: keep in production)

Records whose operator matches nothing in the registry are served with the
honest `Unknown` label rather than being dropped or guessed at. Rationale:

- They are real, named, coordinate-validated fuel locations
  (e.g. "Bombas de Gasolina dos Chineses", "Posto de Abastecimento da
  Tchimucua") — omitting them would make the finder worse at its job.
- `Unknown` is a confidence signal, not a data error: these are
  predominantly **bandeira-branca** independents and other small private
  operators outside the verified brands.
- They are naturally second-class in the UI: no province tags, so they
  appear on the map and in unfiltered views but not in province filters.

The registry keeps shrinking this bucket deterministically (179 → 34 in
the first pass); no fuzzy guessing is used to force it to zero.

### 3.6 Province backfill

OSM records often carry `addr:city`/`addr:municipality` but no
`addr:province` (204 of 279 records lacked province in the 2026-09-23
snapshot). `ingestion/provinces.py` fills the gap deterministically from
an explicit municipality → province table — same data-as-code philosophy
as the brand registry: only observed, unambiguous municipalities are
listed; anything ambiguous stays empty.

- Examples: Lubango → Huila, Ondjiva → Cunene, Quibala → Kwanza Sul,
  Panguila → Bengo, Moçâmedes → Namibe, Malanje → Malange (dataset
  spelling).
- Deliberately excluded: municipalities affected by Angola's 2024 reform
  (18 → 21 provinces, e.g. Funda) until verified; neighborhood names
  misfiled as municipality (e.g. "Bairro da Luz").
- Tagged provinces are never overwritten. Backfilled records carry
  `province_inferred: true`; snapshot metadata records the table version
  and filled count (`province_backfill: {version, filled_count}`).
- Measured 2026-09-23: 60 of 204 empty provinces filled (204 → 144).

### 3.7 Stale reuse keeps rejected records

When a network source fails, the pipeline reuses that source's previous
records — previously only from `stations_clean.json`, which meant a
flaky-network run silently shrank `stations_rejected.json` and destroyed
rejection provenance (observed 2026-09-23: 63 → 1). The stale path now
also reloads the source's previous rejected records; they re-enter the
pipeline and are re-rejected with fresh reasons, flagged `is_stale`.

## 4. Data contract

Additive only: clean records gain `merged_sources` (list of source names)
and `province_inferred` (bool, true when the province was backfilled from
the municipality table). Snapshot metadata gains `province_backfill`
`{version, filled_count}`. No serving-layer changes required.

## 5. Testing

- `canonicalize_operator`: every observed variant → canonical; unknown
  strings → `Unknown`; legal-suffix stripping; name inference;
  registry contains exactly the verified brands.
- OSM tag semantics: `brand` tag preferred over `operator`
  (brand = marketed flag, operator = franchisee); `etu energias`/`somoil`
  → Etu Energias while bare `etu` stays `Unknown` (Bantu word for
  "us/ours"); colloquial `sonangola`/`pumangola` variants.
- Dedupe: OSM-id + branded record < 150 m → one record, branded
  name/operator, `merged_sources` lists both; two different brands
  100 m apart → not merged; same-brand pair 500 m apart → not merged.
- Name hygiene: lone OSM-id record → rejected with reason.
- Existing ingestion tests keep passing (exact-key dedupe case is
  subsumed: distance 0 < 150 m, same operator).
- Dataset contract (`tests/test_dataset_contract.py`): guards the committed
  snapshot itself — operators ⊆ registry + Unknown; zero OSM-id names
  served; Unknown share < 20%; coordinates inside Angola; clean records
  carry `merged_sources`; every rejected record carries reasons. Offline,
  runs in CI on every PR, so silent data regressions fail the build
  instead of reaching production.
- Province backfill (`ProvinceBackfillTest`): observed municipalities map
  to the right province; tagged provinces never overwritten; ambiguous
  and 2024-reform-affected municipalities stay empty; the inferred flag
  survives reprocessing of stale records.
- Stale reuse (`StaleReuseTest`): a failed source reloads its previous
  clean AND rejected records; rejected ones are re-rejected with fresh
  reasons instead of being lost.

## 6. Rollout

1. Merge PR → the regenerated `data/stations_clean.json` ships in the
   PR, so the deploy serves the cleaned snapshot immediately (no wait
   for Monday's workflow).
2. Verify in production: station count drops 418 → 279 (measured 2026-09-23:
   110 near-duplicate pairs merged, 60 unnamed OSM nodes rejected with reasons),
   no `way/*` names in `/api/v1/stations`, brand filter shows the four canonical
   brands + Unknown.
3. Rollback: revert the merge commit (data files revert with it).

## 7. Risks & mitigations

- **Over-merging**: two same-brand sites within 150 m (rare) would merge
  incorrectly. Accepted: the radius is conservative and the alternative
  (visible duplicates) is worse.
- **Under-merging**: same station with > 150 m coordinate error stays
  duplicated. Accepted; improvable with better source data.
- **`Unknown` bucket** (~12% after the first pass; was ~40%). Honest label
  for bandeira-branca independents and other unverifiable operators;
  served in production per the 3.5 policy. Future work can shrink it
  further (better OSM tags, brand inference from imagery — out of scope).
- **Name inference misfire** (e.g. a station named "near Sonangol").
  Only applies when the operator tag is missing; observed names are
  brand-led (`"TotalEnergies - …"`), so risk is minimal.

## 8. Future work

- Per-province sanity spot-checks against brand websites.
- `is_stale` handling already exists for failed sources; unchanged.
- Consider upstreaming brand fixes to OpenStreetMap (out of scope).
