# Architecture

This document describes how the FuelMap Angola is built
and deployed, as verified against the code. It is the single overview
for readers, reviewers and automated tooling: detail lives in the
documents linked from each section, not duplicated here. If a change
alters anything described below, update this document in the same
change.

Verified against commit `2132ad84` (master, after Phase 0 PR 4).

## Overview

One Heroku dyno serves one web process. That process runs a Dash
dashboard and a FastAPI REST API side by side, both reading the same
bundled JSON snapshot. A scheduled GitHub Actions workflow rebuilds
the snapshot weekly from public sources and commits it back to the
repository. There is no database in the serving path, no
authentication, and no real-time data.

```text
Public sources (OpenStreetMap, operator listings, bundled legacy snapshot)
        |
        v
GitHub Actions refresh workflow (Mondays 06:00 UTC, or manual)
  ingestion.sync_stations -> validate -> dedup -> backfills
        |  publication gate blocks bad snapshots before commit
        v
data/stations_clean.json (+ metadata)     data/dataset_versions.json (append-only)
data/stations_rejected.json
        |
        v
Heroku, one dyno, one process (gunicorn app:server)
  PrefixRouter (api/mount.py)
   |-- /api, /health, /docs, /openapi.json, /redoc -> FastAPI (api/main.py)
   +-- everything else                            -> Dash (app.py, use_pages)
        |
        v
Shared read path: data_fetch (300s cache, fallback) -> station_data
(normalize, stable ids) -> Dash pages / FastAPI routers
```

## Serving

- `Procfile` runs `gunicorn app:server`, a single web process.
- `app.py` creates the Dash app with `use_pages=True` and the
  SPACELAB theme, then wraps its WSGI app with `mount_api`
  (`api/mount.py`). `PrefixRouter` routes the API prefixes
  (`/api`, `/health`, `/docs`, `/openapi.json`, `/redoc`) to the
  FastAPI app through an ASGI-to-WSGI bridge (`a2wsgi`); all other
  paths fall through to Dash. FastAPI keeps seeing its full routes,
  so the API contract in `docs/api-deployment.md` matches the code.
- Dash pages: `/` is the map (`pages/map.py`), `/metodologia` is
  the methodology page (`pages/metodologia.py`), and
  `/reportar-erro` is the error-report page
  (`pages/reportar_erro.py`). The navbar has one methodology link;
  the footer is copyright only.
- The map uses Plotly `scatter_mapbox` with the `open-street-map`
  style. There is no Mapbox token in the repository, no satellite
  view, and no Street View.
- `seo.py` provides the page title, meta tags, `robots.txt` and
  `sitemap.xml`. The Flask server in `app.py` serves the last two.
- The Heroku dyno filesystem is ephemeral. Nothing the server
  writes at request time persists, which is why error reports are
  never stored on the server: the report page only generates a
  pre-filled GitHub issue link (`reports.py`).

See `docs/api-deployment.md` for the serving decision record.

## Read path

Both the dashboard and the API read the same files through the same
Python functions, so they cannot drift apart for the same snapshot.

- `data_fetch.get_stations_df()` reads `data/stations_clean.json`
  with a 300-second in-memory cache. If the snapshot is unavailable
  it falls back to the bundled legacy `gas_stations.json` and flags
  the result, instead of failing the page. It returns only station
  rows; it drops the metadata block and per-station provenance.
- `station_data.normalize_stations_df()` produces the canonical
  columns shared by Dash and FastAPI. Station ids are stable and
  deterministic: the first 48 bits of a SHA-256 over operator, name
  and coordinates formatted to 6 decimals. Coordinates outside
  Angola, or `(0, 0)`, are excluded.
- `api/db.py` (`load_stations_df`) is the API's single data
  dependency, returning the normalized frame plus a `live` or
  `fallback` label. `api/deps.py` exposes it so tests can swap the
  dataset with dependency overrides.
- `dataset_meta.load_dataset_meta()` reads only the `metadata`
  block of `data/stations_clean.json`, with its own 300-second
  cache. It is the single source of freshness for the dashboard
  badge and for `GET /api/v1/meta`: freshness is derived from
  `generated_at` only, never from the cache TTL or the deploy date.
  A missing, invalid or future `generated_at` reports
  `unavailable`, never an invented date.
- `dataset_versions.load_dataset_versions()` reads
  `data/dataset_versions.json` and backs `GET
  /api/v1/dataset-versions` and the version list on the methodology
  page. A missing file falls back to one entry derived from the
  current metadata, marked as an unknown publication state.
- `reports.py` is standard-library only: report validation and
  pre-filled issue URL building, with no I/O, no token and no
  personal data.

## Ingestion

See `docs/data-ingestion.md` for the full source strategy,
`docs/data-quality.md` for validation rules, and
`docs/geocoding-backfill.md` for the address and province backfills.

- `ingestion/sync_stations.py` (`build_dataset`) is the entry
  point. Sources: the bundled legacy Pumangol snapshot, the
  OpenStreetMap Overpass baseline, an operator-specific OpenStreetMap
  adapter for Sonangol, and a Pumangol website adapter. No official
  or public government or operator API for Angola fuel stations has
  been identified; the pipeline depends on public sources and their
  weekly availability.
- A failed source reuses its previous clean records, marks them
  `is_stale`, and records the source as `stale_reused` or `failed`
  in `source_status`. Detailed errors stay in ingestion files and
  logs; the public API exposes only source, status, record count
  and the stale flag.
- `ingestion/validate.py` validates and deduplicates: records
  need a name, an operator and usable coordinates inside Angola.
  Deduplication prefers fresh over stale, operator website over
  OpenStreetMap, operator-specific OpenStreetMap over the general
  baseline, and records with an address over records without one.
- Backfills fill empty fields only and never overwrite tagged
  values: `ingestion/provinces.py` fills provinces from an explicit
  municipality table (18 provinces, pre-2024-reform spellings, with
  reform-affected and ambiguous municipalities excluded), and
  `ingestion/geocode.py` fills empty addresses with offline plus
  codes. There is no municipality backfill; missing municipalities
  stay empty, honestly.
- Ingestion computes `metadata.confidence_counts` over the clean
  records only, so the counts sum to `record_count`. Levels:
  `operador_via_listagem_publica` (found in a public operator listing),
  `operador_via_osm`, and `base_publica_osm`. Staleness does not
  change a record's level. Per-station confidence is not exposed:
  provenance does not travel through the read path in Phase 0.
- Outputs are `data/stations_clean.json` and
  `data/stations_rejected.json`, each carrying the same `metadata`
  block. The version registry, `data/dataset_versions.json`, is
  append-only: one entry per published snapshot, keyed by
  `generated_at` (which is also `version_id`), appended in the
  same commit as the snapshot.

## Automation

- `.github/workflows/refresh-stations.yml` runs Mondays at 06:00
  UTC and on manual dispatch: install dependencies, run ingestion,
  run the test suite, run the publication gate
  (`ingestion/publish_gate.py`), append the version entry
  (`ingestion/append_version.py`), then auto-commit the three data
  files. The gate blocks snapshots with a missing or future
  `generated_at`, zero records, a record drop over 30%, or a
  rejected-count rise over 50%; a blocked run commits nothing and
  the previous snapshot stays in production.
- `.github/workflows/ci.yml` runs on pushes to master and on pull
  requests: compile all Python sources, run the test suite, and run
  an offline ingestion check. CI installs only pandas, requests,
  FastAPI, httpx, `a2wsgi` and `openlocationcode`: it does not
  install Dash, so no test may import Dash. Tests that need Dash
  rendering check source text or use a real browser instead.
- There is no separate alert channel for a failed refresh in Phase
  0. The public freshness badge is the control: it turns stale
  after 14 days and overdue after 28 days on its own.

## What this architecture is not

- No database serves requests. `mysqlConnect.py` is a supporting
  script, not part of the serving path.
- No authentication, API keys, rate limiting, paid tier, or
  service-level agreement exists in Phase 0.
- No real-time prices, fuel availability, stock, licensing or
  operating status are published. The data describe station
  identity and approximate location at the snapshot date only.
- No claim of official, operator or regulator validation is made
  anywhere without a written agreement. The methodology page states
  what the project is not, in Portuguese, for Angola users.
- The repository is public and portfolio-facing: code, README,
  docs and API stay in English; site UI strings are in Portuguese.
