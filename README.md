# Louisiana Capital Projects Tracker

An open, source-cited tracker of Louisiana capital projects worth $10M or more: what's being built, where, when, and what it needs. Material estimates are shown with their assumptions.

This is an independent personal project, not affiliated with any employer, agency or project owner. The plan is in [`docs/prd.md`](docs/prd.md).

## Status

| Milestone | State |
|---|---|
| M1 Accounts, access, source terms | Source terms checked ([`docs/sources.md`](docs/sources.md)). Account steps are still for Eliot to do (see below). |
| M2 Data model, license, seed records | Done: schemas, validator, ODbL license, and 6 seed Tier A projects with 13 sources. |
| M3 Collector | Built and tested offline (`pipeline/`, `tests/`, `.github/workflows/collect.yml`). Needs an API key before the first live run. See [`docs/collector.md`](docs/collector.md). |
| M4–M5 Checker, Estimator | Not started |
| M6 Site | Shell built: table, map, profiles, parish overlap, methodology, sources, briefs, sign-up. |
| M7–M9 | Not started |

## Run locally

Only the Python 3 standard library is needed; there's nothing to install.

```sh
python3 scripts/validate.py      # check every record
python3 scripts/build.py         # compile to dist/
python3 -m http.server -d dist 8000   # open http://localhost:8000
```

## Layout

```
data/schema/     JSON Schemas (documentation; enforced by scripts/validate.py)
data/projects/   one JSON file per project
data/sources/    one JSON file per source document, with the exact quotes used
data/estimates/  materials estimates (M5)
data/benchmarks.json  cited material-intensity benchmarks (M5)
site/            static assets, plus vendored Leaflet 1.9.4 (BSD-2-Clause, reviewed 2026-09-30)
scripts/         validate.py, build.py
docs/            PRD, source register, permission request drafts, metrics log
.github/workflows/  validate on PR, deploy to GitHub Pages on push to main
```

## Adding or editing a project

1. Add a source file in `data/sources/` (`src-<publisher>-<topic>-<date>.json`) containing the exact quotes.
2. Add or edit `data/projects/<id>.json`. Every figure needs a `source_id`. The `tier` must match `headline_capex_usd` (A: $1B+, B: $100M–$1B, C: $10M–$100M).
3. Run `python3 scripts/validate.py`.

Seed quotes were gathered with a page-summarizing fetch tool and are marked `quote_verified: false`. Check them against the live pages before public launch.

## Deploy settings (GitHub)

- Settings → Pages → Source: **GitHub Actions**.
- Settings → Secrets and variables → Actions → Variables. These are optional:
  - `SIGNUP_FORM_URL`: the form service's POST endpoint.
  - `ANALYTICS_PROVIDER`: `goatcounter` or `plausible`.
  - `ANALYTICS_SITE_ID`: the GoatCounter code or Plausible domain.
- Later milestones add the secret `ANTHROPIC_API_KEY` (M3).

## Licenses

- Code: MIT ([`LICENSE`](LICENSE)).
- Data: ODbL 1.0 ([`LICENSE-DATA`](LICENSE-DATA)). Attribute as: "Data: Louisiana Capital Projects Tracker, ODbL 1.0".
- Map tiles: © OpenStreetMap contributors.
