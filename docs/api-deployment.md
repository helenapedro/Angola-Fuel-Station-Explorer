# Design: serving the FastAPI REST API from the Dash dyno

## 1. Context

The repo contains two services over the same station dataset:

- **Dash dashboard** — the primary app, deployed on Heroku (`gaspumpmap`,
  auto-deploy from `master`). The `Procfile` runs a single web process:
  `web: gunicorn app:server`.
- **FastAPI REST API** (`api/`, `uvicorn api.main:app`) — added for
  programmatic access to the dataset (`/api/v1/stations`, `/health`,
  `/docs`, …).

Problem (verified 2026-09-23): the API code ships to the dyno, but no
process serves it. `GET https://gaspump.hmpedro.com/api/v1/stations`
returns the dashboard's HTML (the SPA fallback for unknown paths), not
JSON. Deploying the repo is not the same as running everything in it —
Heroku executes exactly one command from the `Procfile`.

## 2. Goals / non-goals

Goals:

- The REST API is reachable in production at
  `https://gaspump.hmpedro.com/api/…` (plus `/health` and `/docs`).
- Zero extra infrastructure cost (no additional dyno).
- No behavior change to the dashboard; local dev (`python app.py`)
  serves both, like production.
- Small, reversible change.

Non-goals:

- Authentication / rate limiting (public read-only API, portfolio
  scale).
- Independent scaling or separate deploy pipeline for the API.

## 3. Options considered

| # | Option | Pros | Cons |
|---|--------|------|------|
| A | Second Heroku app / dyno for the API | Clean separation; independent scaling | Extra monthly cost; two deploys to keep in sync; overkill for a small read-only API |
| B | **Mount FastAPI inside the Flask/Dash WSGI app (chosen)** | One dyno, one deploy; ~30 lines of code; local/prod parity | Shares gunicorn sync workers; needs an ASGI→WSGI bridge dependency |
| C | Switch the web process to uvicorn serving FastAPI, mount Dash inside it | Single process | Far more invasive — Dash is the primary app; rewrites the serving story |
| D | Reverse proxy (e.g. nginx buildpack) routing `/api/*` to a second local port | Separation without a second dyno | Extra moving parts; buildpack complexity for little gain |

**Chosen: B.** The API is small, read-only, and sync — it comfortably
shares the existing dyno.

## 4. Design

New module `api/mount.py`:

- `PrefixRouter`: a WSGI middleware. If the request path is exactly one
  of the API prefixes — or under one of them — the request goes to the
  FastAPI app; everything else falls through to the Dash/Flask app.
- The FastAPI (ASGI) app is adapted to WSGI with
  `a2wsgi.ASGIMiddleware` (pure-python, no transitive dependencies).
- Unlike `werkzeug.middleware.dispatcher.DispatcherMiddleware`, the
  path is passed through **untouched** (no `SCRIPT_NAME` stripping), so
  FastAPI keeps seeing its full routes (`/api/v1/stations`, …).

`app.py`: after `server = app.server`,

```python
server.wsgi_app = mount_api(server.wsgi_app)
```

`requirements.txt`: adds `a2wsgi==1.10.10`.

### Request flow

```
                    ┌─────────────────────────┐
                    │ gunicorn → Flask (Dash)   │
                    │  server.wsgi_app          │
                    └────────────┬──────────────┘
                                 │ PrefixRouter
                ┌────────────────┼────────────────┐
                │ path in        │                │ otherwise
                │ API_PREFIXES   │                ▼
                ▼                │         Dash app (/, /_dash-*)
  ┌─────────────────────────┐    │
  │ ASGIMiddleware          │    │
  │  → FastAPI app          │    │
  │  /api/v1/*, /health,    │    │
  │  /docs, /openapi.json   │    │
  └─────────────────────────┘    │
```

### Path contract

| Public path | Served by |
|---|---|
| `/`, `/_dash-*`, everything else | Dash dashboard |
| `/api`, `/api/v1`, `/api/v1/*` | FastAPI |
| `/health` | FastAPI |
| `/docs`, `/redoc`, `/openapi.json` | FastAPI (interactive docs) |

The prefix set lives in `api/mount.py` as `API_PREFIXES` — this doc and
the code describe the same contract; change both together.

## 5. Testing

- **Unit** (`tests/test_mount.py`): routing with stub WSGI apps —
  prefix match, sub-paths, fall-through, near-miss paths (`/apiary`,
  `/healthy` must NOT match), and `PATH_INFO` preservation.
- **Manual smoke** (local): `werkzeug.test.Client` against the combined
  app — `GET /api/v1/stations?page_size=1` returns JSON with `items`;
  `GET /` returns dashboard HTML; `GET /docs` returns the Swagger page.
- **CI**: existing suite plus the new tests (`a2wsgi` added to the CI
  install line so the test env mirrors prod imports).

## 6. Rollout

1. Merge the PR → Heroku auto-deploys `master`.
2. Verify in production:
   - `curl https://gaspump.hmpedro.com/api/v1/stations?page_size=1` → JSON
   - dashboard still loads; `/docs` renders.
3. Rollback: revert the merge commit. The dashboard is unaffected — the
   router only *adds* prefixes, it never intercepts existing paths.

## 7. Risks & mitigations

- **ASGI→WSGI bridging under sync workers.** `ASGIMiddleware` runs the
  app's event loop per request; all our endpoints are sync `def` (run in
  Starlette's threadpool), so there is no `asyncio` contention.
- **Upstream fetch blocking a worker.** On a cache miss the 5s upstream
  fetch blocks one gunicorn sync worker — pre-existing behavior,
  unchanged; the 5-minute in-memory cache absorbs steady state.
- **Path conflicts.** If the dashboard ever needs its own `/api/*`
  routes, the reserved prefixes in `API_PREFIXES` must be revisited.
- **CORS** remains `allow_origins=["*"]` on the API — unchanged,
  acceptable for a public read-only API.

## 8. Future work

- If API traffic outgrows the shared dyno, split to a dedicated
  app/dyno (option A) — the API code needs no changes for that move.
- Revisit `requirements.txt` hygiene (dev/prod split) independently.
