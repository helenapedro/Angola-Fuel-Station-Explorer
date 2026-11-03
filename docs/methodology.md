# Methodology

Last reviewed: 2026-11-02.

This document is the public, English-language summary of how FuelMap Angola
collects, checks, dates, and publishes its fuel station data. It is written
for anyone who needs to decide whether to trust a snapshot: a driver, a
researcher, or a partner. The full, authoritative version is the methodology
page on the live site, in Portuguese, at `/metodologia`. If the two ever
disagree, the live page and the API response at `/api/v1/meta` are the
current record.

Figures in this document are stable rules, not current counts. For the
current snapshot date, record count, rejected count, and quality-level
counts, see `/api/v1/meta` on the live site.

If a sentence here is unclear, treat it as a limit of the project, not as a
promise.

## What this project is

FuelMap Angola is a discovery dataset of fuel stations in Angola,
searchable by operator, province, municipality, or station name. Each record
identifies one station and its approximate location, as of the date of the
source it came from, and can be cited through the snapshot date.

The project is also a transparency record. It shows the origin and state of
each source, the snapshot generation date, the number of records and rejected
records, and the freshness state. Being open about limits is part of the
product, not a detail.

## What this project is not

This project is not a state register, and it does not replace any operator
list. No public body and no operator has reviewed, approved, or confirmed
this data for this project, and no operator supports this project. There is
no partnership behind this dataset.

It is not a complete or exhaustive list of every fuel station in Angola.
Coverage is partial, and the gaps are part of the information.

It does not say whether a station is open right now, whether it has fuel,
what the price is, or whether it is licensed. It is not a real-time
operations tool, and it must not be used as the only basis for critical
decisions, such as sending a fleet or planning a critical route, without
confirmation on site or with the operator.

## Where the data comes from

The starting base is OpenStreetMap, with fuel station records in Angola.
Public operator listings, such as Sonangol and Pumangol, are added when
available. Public records are also filtered by operator brand. The list of
sources and the state of each source in each snapshot are shown at the top
of the methodology page and at `/api/v1/meta`.

No public fuel station API in Angola, from public bodies or from operators,
has been identified that could serve as the main source. Collection
therefore depends on public sources and on their availability each week.

Attribution: OpenStreetMap data is (c) OpenStreetMap contributors, available
under the Open Database License (ODbL). Operator listings keep the terms of
their own sites.

## What a record means

A record enters the map only if it passes validation: a name is present, an
operator is present, coordinates are valid and inside Angola, with no
missing coordinates and no coordinates at the map zero point, and no stray
formatting characters. Records that fail go to the rejected records and
never appear on the map. Passing validation means the record can be used
for location discovery. It does not mean the station is open or operating.

A record is treated as reliable for discovery when it passed validation,
has an identified source, is not marked as outdated, and belongs to a
snapshot less than 14 days old. Even then, it speaks only to the identity
and location of the station on the source date, not to its current state.

### Signs of an incomplete record

- Missing address, or an address that is only a location code (plus code).
- Province inferred from the municipality.
- Municipality missing, or filled in by a fallback rule from the province.
- Generic name, identical to the operator name.

An incomplete record is a starting point, not a complete file.

### Signs of a possibly outdated record

- The record is marked as outdated.
- Its source failed or was reused in the latest generation.
- The whole snapshot is more than 14 days old.
- The source public page changed or stopped responding.

Outdated records are not deleted without evidence. They stay visible and
marked until they are confirmed or corrected in a later version.

## Quality levels by source

Quality depends on the source. The table below says how to read each level.
Levels are aggregate counts: if most records are public-base records, the
methodology must show that, not dilute the lowest level.

| Level | What it means | How to use it |
|---|---|---|
| `base_publica_osm` | Public information, useful for discovery, with no operator confirmation. | Discovery only. Confirm before deciding. |
| `operador_via_osm` | Public record filtered by operator brand. Higher quality than the public base, still with no direct confirmation. | Discovery with more confidence, still with no direct confirmation. |
| `operador_via_listagem_publica` | Record found in a public operator listing, on the stated date. The highest level in this project. | Discovery. It does not prove the station is open, has fuel, is licensed, or that the operator supports this project. |

In Phase 0, `operador_via_listagem_publica` means only that the record was
found in a public operator listing. It does not mean the operator supplied
the data under an agreement, and it does not mean the operator confirmed the
data for this project. A level for data supplied directly under an agreement
can only be used with a written agreement with the operator. Until then,
that label does not exist in the dataset.

## How duplicate records are handled

Two records are treated as the same station when they have the same
operator, the same name after unifying case, accents, and spacing, and
coordinates rounded to 4 decimal places. When duplicates exist, the
preference order is: a fresh record over an outdated one; a public operator
listing over OpenStreetMap; a brand-filtered record over a general record;
a record with an address over a record without one.

## What the data represents, and what it does not

The data represents the identity and approximate location of fuel stations
in Angola found in identified public sources, on the snapshot date. It is a
discovery base, searchable and citable.

The data does not represent the current operating state of a station, fuel
availability, prices, licensing, or a complete list of every station in the
country.

When the source has low confidence, or when the record is marked as
outdated, treat the data only as an approximate indicator, for discovery.
Confirm on site or with the operator before any operational decision.

When the address is only a plus code, the province was inferred, the
municipality came from a fallback rule, or the name is generic and identical
to the operator, the record is only approximate, even if it appears on the
map with coordinates.

## Freshness and updates

The only update date is the snapshot generation date, published at
`/api/v1/meta` and in the badge next to the counters on the map. It is not
the date the site was published.

The freshness threshold is 14 days, because collection is weekly and needs
margin. Up to 14 days, a snapshot counts as fresh. From 15 to 28 days, it
counts as outdated, with a visible warning next to the map. Over 28 days,
it counts as overdue, with a visible warning and a dated owner note on the
methodology page.

If the generation date is missing, invalid, or in the future, the site and
the API show the date as unavailable. A date is never invented.

To cite a snapshot, always cite the generation date and the version
identifier, which in this phase is the same as the generation date, not
just the site name. If the snapshot is more than 14 days old, treat it as
historical, not current.

## Refresh governance

Dataset owner: Helena Pedro, sole owner. The owner triggers manual
collections, reviews automatic collection failures, reviews corrections
received, approves publications, and publishes dated overdue notes.

Planned frequency: automatic weekly collection, on Mondays at 06:00 UTC.
This rhythm is a public target, not a contractual promise to publish every
Monday.

Before a new version is published, it must pass a check: tests pass, the
data file is valid, the generation date is present and not in the future,
and the record count is above zero. If the check fails, there is no new
version, and the previous snapshot stays in production, growing older, with
the warning appearing automatically after 14 days.

When a single source fails, the previous records from that source are
reused and marked as outdated, and the failure stays visible at
`/api/v1/meta` and on the methodology page. When collection fails as a
whole, or a test fails, there is no new snapshot. The failure stays in the
automatic collection record, and in this phase there is no other alert
channel: the freshness badge itself is the control, and it cannot be
suppressed.

Public time targets, which are not contractual promises: the owner reviews
an automatic collection failure within 7 calendar days, or at the next
planned collection, whichever comes first, and records the decision, which
may be to rerun, to fix the source connection, or to leave the warning
visible. Accepted corrections enter only the next published snapshot, and
are never edited into the current snapshot. If the age passes 28 days, the
methodology page must show a dated note with the known cause and the next
step, or a note pausing the weekly rhythm. A warning growing in silence is
not acceptable.

In this phase there is no formal backup owner, no 24 hour support, and no
service availability promise. The service runs on a single server.
Governance must be reviewed before any commitment to a paying partner.

## Version history

Each published snapshot is recorded with its date, counts, and state at
publication. Versions are never rewritten: a week with no publication shows
as a gap, not filled in. Always cite the version used, which in this phase
is the same as the generation date. The full history is available at
`/api/v1/dataset-versions` and on the methodology page.

## How to report an error

A no-account form for reporting errors is published: no GitHub account is
needed to report. The link is on the methodology page, with the same
fields: station identifier, snapshot date used, problem type, and a public
source if possible. No name, email, phone, or user location is asked for.

It is also possible to open a public correction request in the project
repository, with the same fields. That requires a GitHub account:
https://github.com/helenapedro/fuelmap-angola/issues/new

An accepted correction appears only in a later version, and is never edited
into the current snapshot, so that each version stays citable and
verifiable.

## API

The dataset is also served as a JSON REST API from the same snapshot:

- `GET /api/v1/stations` (paginated; filters: province, operator, search)
- `GET /api/v1/stations/{id}`
- `GET /api/v1/stations/stats`
- `GET /api/v1/meta`
- `GET /api/v1/dataset-versions`
- `GET /health`

Interactive API docs are at `/docs` on the live site. See
`docs/api-deployment.md` for how the API is served, and
`docs/architecture.md` for the full overview.
