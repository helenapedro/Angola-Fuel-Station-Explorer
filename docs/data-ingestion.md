# Station Data Ingestion

There is no documented official/public Angola fuel-station API currently identified for government, Sonangol, Pumangol, Galp/Sonangalp, or regulator-style station data. The project should therefore treat data collection as a controlled multi-source ingestion process.

## Source Strategy

1. OpenStreetMap baseline
   - Query Angola fuel stations from Overpass API using `amenity=fuel`.
   - This provides a public, refreshable geospatial baseline.
   - OSM can be incomplete or inconsistently branded, so it is not enough by itself.

2. Operator website adapters
   - Maintain one source adapter per operator website.
   - Current scaffold includes Pumangol in `ingestion/sources/pumangol.py`.
   - Add Sonangol, Galp/Sonangalp, and other operators as separate adapters when their station pages are confirmed.

3. Validated output
   - The Dash app should read only validated station data.
   - Raw source failures should not break app startup or user page loads.

## Output Files

`python -m ingestion.sync_stations` writes:

- `data/stations_clean.json`: records accepted by validation and safe for the dashboard.
- `data/stations_rejected.json`: records rejected with `rejection_reasons` for manual review.

The clean output uses this shape:

```json
{
  "metadata": {
    "generated_at": "2026-07-10T00:00:00+00:00",
    "record_count": 1,
    "rejected_count": 0,
    "source_status": [
      {
        "source": "Pumangol",
        "status": "loaded",
        "record_count": 1,
        "is_stale": false
      }
    ],
    "source_errors": []
  },
  "stations": [
    {
      "operator": "Pumangol",
      "station": "Example",
      "address": "Example address",
      "province": "Luanda",
      "municipality": "Luanda",
      "country": "Angola",
      "latitude": -8.839,
      "longitude": 13.289,
      "source_type": "operator_website",
      "source_name": "Pumangol",
      "source_url": "https://www.pumangol.co.ao/pt/institucional/mapa-de-postos-de-abastecimento",
      "source_id": "Example",
      "scraped_at": "2026-07-10T00:00:00+00:00"
    }
  ]
}
```

## Commands

Build from the bundled legacy JSON only:

```powershell
python -m ingestion.sync_stations --offline
```

Validate the bundled legacy JSON without writing outputs:

```powershell
python -m ingestion.sync_stations --offline --check
```

Build from legacy JSON plus live OSM/Pumangol sources:

```powershell
python -m ingestion.sync_stations
```

Run the old entrypoint, now a compatibility wrapper:

```powershell
python scrap.py
```

## Validation Rules

Records are rejected when:

- station name is missing
- operator is missing
- latitude/longitude are missing or non-numeric
- coordinates are `0,0`
- coordinates are outside Angola bounds
- text still contains obvious encoding or HTML entity artifacts

## Source Status and Stale Records

Every dataset includes `metadata.source_status`. Each source reports:

- `source`: source adapter or snapshot name
- `status`: `loaded`, `failed`, or `stale_reused`
- `record_count`: number of records contributed by that source
- `is_stale`: whether contributed records came from a previous clean dataset
- `error`: present when a live source failed

When a live source fails and a previous `data/stations_clean.json` exists, the sync command reuses the prior clean records for that source and marks each reused record with:

```json
{
  "is_stale": true,
  "stale_reason": "source failure message"
}
```

This keeps one failing adapter from emptying the production dashboard for that operator. If no previous records exist for the failing source, the source is reported as `failed` and contributes no records.

## Deduplication Rules

Records are deduplicated by normalized operator, normalized station name, and coordinates rounded to 4 decimals. When duplicates exist, the pipeline prefers:

1. fresh records over stale records
2. operator website records over OpenStreetMap records
3. records with an address over records without an address

## Operational Guidance

- Schedule the ingestion command weekly unless product requirements need fresher data.
- Keep the dashboard read-only: it should never scrape operator websites during page rendering.
- Store source metadata on every station so stale or disputed records can be audited.
- If one source fails, review `metadata.source_status` and `metadata.source_errors`.
- Add parser tests for every operator adapter before relying on it in scheduled ingestion.

## GitHub Automation

The repository includes two GitHub Actions workflows:

- `.github/workflows/ci.yml`
  - Runs on pushes to `master`/`main` and on pull requests.
  - Compiles Python sources.
  - Runs unit tests.
  - Validates the offline dataset from the bundled legacy JSON as a smoke check without rewriting output files.

- `.github/workflows/refresh-stations.yml`
  - Runs every Monday at 06:00 UTC and can also be triggered manually from GitHub Actions.
  - Runs `python -m ingestion.sync_stations` against live sources.
  - Runs ingestion tests.
  - Commits changed `data/stations_clean.json` and `data/stations_rejected.json` back to the branch.

After each scheduled refresh, inspect the generated `metadata.source_status` before trusting the new dataset. A successful workflow can still contain `stale_reused` source status if one operator website or OSM was unavailable during the run.
