# Louisiana Capital Projects Tracker (v1) PRD

**Status:** Draft, 2026-09-30
**Owner:** Eliot Brooks
**Surface:** New public GitHub repo (personal account). Site served by GitHub Pages; data pipeline runs as scheduled GitHub Actions calling the Claude API.

## Problem

Capital is pouring into Louisiana: LED reports $183B of announced investment in 2026 and nearly $260B since 2024. But the information about which projects exist, what phase they are in, and what materials they will need is spread across press releases, permits, utility dockets and parish agendas. The trackers that exist today (Louisiana AI Hub, LouisianAI, Cleanview) focus on data centers and power. They leave out materials, suppliers and bid timing, and they don't give a single open view of non-data-center megaprojects such as LNG, steel, ammonia, the spaceport and chemicals.

Local tier-2 suppliers can't see what is coming or when, and some have lost work to out-of-state firms. Owner-side procurement and sustainability leads don't have a local view of supply.

v1 is a free, open, mostly automated tracker of Louisiana capital projects worth $10M or more. It shows phase timing and material estimates with the assumptions visible. It is the base asset for a later supplier directory and a low-carbon materials broker. Neither of those is in this PRD.

We want to:
1. Publish an open, source-cited dataset of Louisiana capital projects worth $10M or more, including data centers, LNG, chemicals, ammonia, steel, manufacturing and the spaceport.
2. Show estimated concrete, steel and phase timing for each project, with the method, tier and assumptions visible.
3. Show cross-project synthesis, starting with parish-level overlaps in peak construction.
4. Run the pipeline with minimal owner time: agents collect, check and estimate, and a human reviews only the risky changes.
5. Build an audience of tier-2 suppliers now, and later owner-side procurement leads, who will be the users of the phase-2 directory.

**Success metric:** About 100 weekly unique visitors to the site, 3 months after public launch, measured with privacy-friendly site analytics. The baseline is 0 because the site is new. Analytics goes live before launch (M1/M6).

## Constraints

- **Freedom:** Free hand. This is a personally owned project and the real v1, not a throwaway prototype.
- **Touches:** It publishes a public website and dataset. It sends automated requests to government websites (LED, LPSC, LDEQ, parish sites). It collects email addresses (personal data) through a third-party form. It spends on a personal Anthropic API account.
- **Build on / must not disturb:** It has no link to any Cocoon Carbon system, account, domain, data or device. Everything runs under personal accounts. It does not reuse Louisiana AI Hub data; see "Reuse check" in the handoff. We link to them, and we don't republish their records.
- **Data & safety:**
  - Email sign-ups are stored only in the form service's private storage. They never go into the repo, public or private.
  - No emails are sent in v1. Sending is out of scope.
  - Scraping must respect each source's terms, robots.txt and a polite rate limit. Every source's terms are checked and logged before its collector is turned on (M1).
  - Material estimates must always be labelled as estimates, with a range and a link to the method.
  - Auto-merge is limited to the rules in M4. Anything else waits for Eliot to review.
- **Clearance:** Eliot reports that the employer's board and legal checks are already cleared (handoff decision 5). The PRD takes this as given. Any conditions they attached should be added here before M1 closes.

## Decisions captured (from scoping conversation)

| Question | Decision |
|---|---|
| Scope of this PRD | Tracker v1 only. The supplier directory and the materials broker are future PRDs. |
| First audience | Tier-2 suppliers use the tracker in v1. Owner-side procurement leads are the target for the phase-2 contractor/supplier directory. |
| Supplier directory | Deferred to phase 2. It is not in v1. |
| Project types | All capital projects: data centers, LNG, chemicals, ammonia, steel, manufacturing, spaceport and other. |
| Size threshold | $10M or more of announced or filed capital cost. |
| Coverage tiers | Tier C is under $100M: basic record plus a formula estimate. Tier B is $100M to $1B: formula estimate refined with permit facts, reviewed by Eliot. Tier A is $1B or more: bottom-up estimate from public filings, checked against benchmarks, shown as a low/likely/high range, reviewed by Eliot. |
| Materials estimates in v1 | Yes: concrete, steel and phase timing, shown with ranges and a visible method and labelled as estimates. |
| Sources | All available public primary sources: LED announcements, LDEQ EDMS permits, LPSC dockets, ITEP and Board of Commerce & Industry (BC&I) notices, and parish agendas. Each one is gated by a terms-of-use check. |
| Data-center layer | Built from primary filings ourselves. The site links to Louisiana AI Hub and LouisianAI but does not copy their data. |
| Additional project fields (decided 2026-10-04) | Recorded only when a source states them: expected job creation (permanent direct, indirect and total; construction at peak and over the whole build), expected completion date (with whether it means build complete, first operations or full operations), main contractors and key suppliers with their role, site acreage, permit and docket numbers, ITEP application number and approval date, and company-level procurement links. Named individuals' contact details are never stored. |
| Where the new fields show | Projects table: expected completion, permanent jobs and main contractor. Project pages: every field. CSV and JSON downloads: every field. Peak construction workforce now lives in the jobs list (`construction_peak`). |
| Collector scope and schedule (decided 2026-10-04) | All five approved sources: LED news, LED BC&I/ITEP PDFs, Vermilion, Ascension and Cameron. Runs only when started by hand (changed from weekly on 2026-10-04). Backfill from 2025-01-01. Max 40 documents, 200 web requests and $1.50 per run. |
| Collector output (decided 2026-10-04) | One rolling pull request on a `collector` branch. A run continues on it while it's open, so nothing is processed twice. |
| PDF text (approved 2026-10-04) | The workflow installs `poppler-utils` (`pdftotext`) from the Ubuntu archive, so quotes from PDFs can be checked. |
| Claude API mode (decided 2026-10-04) | Regular Messages API, not the Batch API. Weekly runs are small and the $1.50 cap bounds cost; Batch would need runs to wait up to 24h. Revisit if volume grows. |
| Conflicting figures (e.g. Meta Hyperion $10B/$27B/$50B+) | Show every sourced value with its citation. Headline figure is the most recent primary-source value (implied - confirm). |
| Build approach | A real site built with Claude Code. |
| Hosting | Public GitHub repo, with GitHub Pages for the site and GitHub Actions for scheduled pipeline runs. |
| Agents | Collector, Checker, Estimator and Brief writer. Each pipeline run opens a pull request. |
| Review gate | Low-risk changes auto-merge: high-confidence facts on projects under $1B that pass the Checker. Eliot reviews and merges every Tier A profile, every estimate change, and anything the Checker flags. |
| Owner time | As automated as possible. Eliot's time is spent reviewing flagged pull requests. |
| API budget | Under $25 a month. Haiku for collection, Sonnet for checking and Tier A estimates, and the Batch API wherever the step isn't time-sensitive. |
| Updates channel | Weekly brief published on the site. An email sign-up collects addresses, but nothing is sent in v1. |
| Sign-up storage | A third-party form service (Formspree, Tally or a Google Form; chosen in M1). Exported to CSV when needed. |
| Traction measure | Site analytics: weekly unique visitors, using privacy-friendly analytics (Plausible or GoatCounter; chosen in M1). |
| Dataset license | ODbL 1.0 for the data. Site code under MIT (implied - confirm). |
| Site views in v1 | A filterable table, a map, project profile pages and a parish overlap view. |
| Paywall / accounts | None. Everything is open, and the email sign-up is optional. |
| Distribution | A manual launch to the roughly 20 people on the test list from the handoff, plus a weekly LinkedIn post of the brief (implied - confirm). |
| Commercial use of Pages | v1 is non-commercial, which fits GitHub Pages' rules. The broker or any paid tier would need a different host (see Out of scope). |

## Implementation milestones

Dependency graph: M1 → M2 → M3 → M4 → M5. M2 → M6 (can run alongside M3–M5). M4 + M5 + M6 → M7. M3 → M8. Everything → M9.

### M1 - Accounts, access and source terms

This milestone sets up every account, secret and permission before any build work. It is a dependency for everything else.

- [ ] **Initialize permissions/access.** Confirm or create everything the build needs in one batch while Eliot is at the keyboard:
  - a personal GitHub account and a new public repo (e.g. `la-capital-projects`), with admin rights to it;
  - GitHub Pages enabled, with the source set to GitHub Actions;
  - Actions allowed to create and approve pull requests (repo setting: Workflow permissions set to read and write, and "Allow GitHub Actions to create and approve pull requests" turned on);
  - a branch protection rule on `main` that lets the auto-merge bot through only for PRs labelled `auto-ok`;
  - a personal Anthropic API key stored as the repo secret `ANTHROPIC_API_KEY`, with a monthly spend limit set in the Anthropic Console (illustrative $25 - confirm);
  - a form service account and form created, with its endpoint URL stored as the repo variable `SIGNUP_FORM_URL`;
  - an analytics account created, with its site ID stored as `ANALYTICS_SITE_ID`;
  - optionally, a custom domain registered personally, with DNS pointed at Pages.
- [ ] Confirm that no Cocoon account, email, laptop profile or domain is used anywhere above.
- [ ] Record any conditions the board or legal attached to the clearance in the Constraints section.
- [ ] Create `docs/sources.md` with one row per source: URL, access method (HTML, RSS, search portal, PDF), terms-of-use URL, a robots.txt summary, reuse terms, the rate limit we will apply, and a status of `approved`, `blocked` or `ask`.
- [ ] Check terms for LED news and project pages.
- [ ] Check terms for LDEQ EDMS.
- [ ] Check terms for the LPSC Document Access Center.
- [ ] Check terms for the LED BC&I/ITEP board postings.
- [ ] List parish agenda sources, starting with the parishes of known Tier A projects: Richland, Vermilion, Ascension, Cameron, Calcasieu, Plaquemines and St. James (illustrative list - confirm). Check terms for each.
- [ ] For any source marked `ask`, draft a short permission email in `docs/source-requests.md` for Eliot to send. Nothing is sent automatically.
- [ ] Choose the form service and the analytics tool, and record both in the Decisions table. Check that the form service's free tier fits (illustrative 100+ submissions a month - confirm).
- [ ] Baseline: analytics snippet is live on a placeholder page, so launch-day traffic is captured from day one.

### M2 - Data model, license and seed records

This milestone defines the schema that every agent writes to, and seeds it by hand with known projects. It depends on M1.

- [x] `data/schema/project.schema.json` with these fields (plus the 2026-10-04 additions in the Decisions table):
  - `id` (a slug)
  - `name`
  - `owner_company`
  - `type` (enum: `data_center`, `lng`, `chemicals`, `ammonia_hydrogen`, `steel_metals`, `manufacturing`, `spaceport_aerospace`, `power_generation`, `infrastructure`, `other`)
  - `parish`
  - `lat` and `lon` (nullable)
  - `capex_values[]` (each with `value_usd`, `source_id`, `as_of`)
  - `headline_capex_usd`
  - `tier` (A, B or C, derived from `headline_capex_usd`)
  - `status` (enum: `announced`, `permitting`, `approved`, `under_construction`, `operational`, `paused`, `cancelled`)
  - `phases[]` (each with `name`, `start`, `end`, `source_id` or `estimated: true`)
  - `peak_workforce` (nullable, sourced)
  - `estimate_id` (nullable)
  - `confidence` (HIGH, MEDIUM or LOW)
  - `first_seen` and `last_verified`
  - `source_ids[]`
- [ ] `data/schema/source.schema.json` with these fields: `id`, `url`, `publisher`, `doc_type` (enum: `press_release`, `air_permit`, `water_permit`, `docket_filing`, `itep_notice`, `parish_agenda`, `news`, `other`), `retrieved_at`, `snapshot_path`, `quote` (the exact extract that supports the claim), and `terms_status`.
- [ ] `data/schema/estimate.schema.json` with these fields: `project_id`, `tier`, `method_version`, `concrete_m3` (`low`, `likely`, `high`), `steel_t` (`low`, `likely`, `high`), `assumptions[]` (each with `text` and `source_id` or `benchmark_id`), `reviewed_by`, and `reviewed_at`.
- [ ] Storage: one JSON file per record under `data/projects/`, `data/sources/` and `data/estimates/`. A build step compiles these into `site/data/projects.json`, `projects.csv` and `projects.geojson`.
- [ ] Add `LICENSE-DATA` with the full ODbL 1.0 text and `LICENSE` (MIT) for code. Add a README section with the attribution line: "Data: Louisiana Capital Projects Tracker, ODbL 1.0".
- [ ] Add a schema validation script (`npm run validate`) that fails on any record missing required fields or with a `source_id` that doesn't resolve.
- [ ] Hand-enter the seed Tier A records from the handoff, each with a primary source and a snapshot:
  - SpaceX, Vermilion Parish
  - Meta Hyperion, Richland Parish, with all three conflicting capex values
  - Hyundai Steel, Ascension Parish
  - at least two LNG, ammonia or chemical projects (to be identified in M1 research)
- [ ] Raw source snapshots (HTML or PDF text) are saved under `data/snapshots/`, with a size cap per file (illustrative 2 MB - confirm) so the repo stays under 1 GB.

### M3 - Collector agent

This milestone pulls each approved source and extracts candidate project records. It depends on M2.

- [x] One source adapter per source in `pipeline/sources.py`. Each one lists new items since the last run, and the runner saves a text snapshot. The User-Agent names the project and links the repo instead of an email. Each host waits at least the seconds set in `docs/sources.md`, robots.txt is checked (redirects included), and blocked hosts are refused.
- [x] Adapters built for every `approved` source: LED news, BC&I/ITEP PDFs, Vermilion, Ascension (CivicClerk API) and Cameron (RSS). LPSC (ask) and LDEQ EDMS (blocked) are not included.
- [x] Extraction uses Haiku 4.5 through the regular Messages API (see Decisions). It fills a candidate record from the schema and must quote the supporting text verbatim for each field. This includes the fields added on 2026-10-04 (jobs, expected completion, contractors, site acreage, permits, ITEP, procurement links). It never infers a capex figure, and it drops any field it can't back with a quote.
- [x] Filter: drop candidates whose capex is below $10M or unknown. Unknown capex goes to `data/review/unknown-capex.json` so it isn't lost.
- [x] Workflow `collect.yml` runs only on manual `workflow_dispatch` (no schedule), with a free dry-run option. It writes candidates to `data/candidates/` on the rolling `collector` branch and pull request.
- [x] Each run writes a run log to `data/runs/<date>.json` with items fetched, candidates, failures and token cost.

### M4 - Checker agent and review gate

This milestone verifies each candidate, removes duplicates, and decides whether it can auto-merge or needs Eliot's review. It depends on M3.

- [ ] The Checker uses Sonnet 5.5. It re-opens the snapshot, confirms each quoted field appears verbatim in it, and sets `confidence`:
  - HIGH: every field quote-matches and the source is a primary government or company document.
  - MEDIUM: fields match, but the source is news only.
  - LOW: something is partial or inferred.
- [ ] Dedupe: match candidates to existing projects on normalized owner, parish and type, plus a name similarity check. The Checker writes `merge_into: <id>` or `new`. Ambiguous matches are flagged.
- [ ] Conflict handling: a new capex value that differs from existing values is appended to `capex_values[]`. The headline figure is not overwritten without review.
- [ ] The pipeline opens one pull request per run, with a summary table in the PR body (new projects, updates, flags, cost).
- [ ] Auto-merge label `auto-ok` is applied only when all of these hold:
  - `tier` is B or C;
  - `confidence` is HIGH;
  - the change is not a new headline capex figure;
  - there is no dedupe ambiguity;
  - there is no estimate change.

  Everything else gets `needs-review`, and Eliot is assigned.
- [ ] If an auto-merge PR fails schema validation, the pipeline removes `auto-ok` and adds `needs-review`.
- [ ] Add a weekly digest issue listing every open `needs-review` PR, so review happens in one sitting.

### M5 - Estimator agent and methodology

This milestone produces concrete, steel and phase estimates by tier, with the method published. It depends on M4, because it only estimates checked records.

- [ ] Write `docs/methodology.md`, published on the site. It covers the tier definitions, formulas, benchmark sources, how the ranges are built, a limitations statement, and a version number (starting at `v0.1`).
- [ ] Benchmarks table `data/benchmarks.json`: material intensity per unit for each project type, for example concrete m³ per MW for a data center, steel tonnes per Mt/yr for an EAF mill, and per MTPA for LNG. Every benchmark carries a cited source. No uncited benchmark is allowed: all values are TBD until sourced in this milestone.
- [ ] Tier C formula: intensity per $M of capex for each project type, giving a low/likely/high range. Auto-generated.
- [ ] Tier B: start from the Tier C formula, then refine it with capacity or footprint facts pulled from permits by Sonnet 5.5, citing the permit. Always goes to `needs-review`.
- [ ] Tier A: a bottom-up estimate built from filed capacity, site plans and environmental documents, cross-checked against benchmarks. Output is a range, and each assumption links to a source or benchmark. Sonnet 5.5 drafts it, and it always goes to `needs-review`.
- [ ] Phase timing: use sourced dates where they exist. Otherwise estimate phases from typical durations for each project type in `data/benchmarks.json`, and mark them `estimated: true`.
- [ ] Every estimate stores `method_version`. When the method changes, the version goes up and a re-estimate PR is opened.

### M6 - Public site

This milestone builds the static site that reads the compiled data files. It depends on M2, and can be built alongside M3–M5 using seed data.

- [ ] Choose a static site generator (e.g. Astro or Eleventy - builder's choice). The site deploys through a Pages Actions workflow whenever `main` changes.
- [ ] Home page hero copy: "Every Louisiana capital project over $10M: what's being built, where, when, and what it needs." Sub-line: "Open data. Sources on every figure. Material estimates shown with their assumptions."
- [ ] Filterable table: filter by type, parish, tier, status, capex range and confidence. It has sortable columns, and CSV/JSON download buttons for the current filter.
- [ ] Map: one marker per project with a known lat/lon, and a parish-centroid fallback shown as "approximate location". Markers are coloured by type, and clicking one opens the profile.
- [ ] Project profile page (`/projects/<id>/`):
  - facts, with every figure footnoted to its source;
  - all conflicting capex values listed;
  - a phase timeline;
  - a materials range table with the badge "Estimate · method v0.x · [How we estimate]";
  - the confidence label;
  - `last_verified`.
- [ ] Parish overlap view: a heatmap of parishes (rows) by quarter (columns), showing the count of projects in the construction phase, plus the sum of `peak_workforce` where it is sourced. Estimated phases are shown hatched.
- [ ] Methodology page (from M5) and a Sources page listing every source with its terms status.
- [ ] Sign-up block copy: "Get the weekly Louisiana capital projects brief. Leave your email and we'll let you know when email delivery starts. We only use it for the brief." The block posts to `SIGNUP_FORM_URL`, and nothing is stored on the site.
- [ ] Footer copy: "Data licensed ODbL 1.0. Independent personal project; not affiliated with any employer, agency or project owner. Estimates are indicative, not engineering quantities." Plus links to Louisiana AI Hub and LouisianAI for deeper data-center coverage.
- [ ] Analytics snippet on every page. No cookies banner is needed if the analytics tool is cookieless (verify with the chosen tool in M1).

### M7 - Weekly brief and launch

This milestone publishes the weekly brief on the site and launches to the first audience. It depends on M4, M5 and M6.

- [ ] The Brief writer agent (Sonnet 5.5) runs weekly (illustrative: Monday 07:00 Central - confirm). It drafts `site/briefs/<yyyy-mm-dd>.md` covering new projects, status changes, new estimates and one parish-overlap insight. Every claim links to its project page.
- [ ] Every brief PR is labelled `needs-review`. A brief is never auto-published.
- [ ] Add a brief archive page and an RSS feed of briefs (a free by-product of the static site).
- [ ] Launch checklist: at least 5 Tier A profiles are reviewed and published, and at least 25 total records (illustrative - confirm).
- [ ] Draft the launch message and a post-launch LinkedIn template in `docs/launch.md`. Eliot sends and posts them himself; nothing is posted automatically.
- [ ] Record the launch date in `docs/metrics.md`. The 3-month success check falls on launch date + 13 weeks.

### M8 - Operations, cost and resilience

This milestone keeps the pipeline running, within budget, and visible when it breaks. It depends on M3.

- [ ] Cost guard: each run adds up token cost in its run log. If the month-to-date cost goes over 80% of the budget (illustrative $20 of $25), non-essential runs pause (Tier C refresh first) and an issue is opened.
- [ ] Keep-alive: the weekly pipeline commit counts as repository activity. Add a check that fails loudly if there has been no commit for more than 45 days, because scheduled workflows in public repos are disabled after 60 days without activity.
- [ ] Failure alerts: any collector failing 3 runs in a row opens a GitHub issue that names the source (GitHub notifies Eliot by email).
- [ ] Source change detection: if an adapter returns 0 items for N runs where it usually finds items, it opens an issue (illustrative N = 7 - confirm).
- [ ] Repo size check: fail the build if the repo goes over 800 MB, to stay under Pages' 1 GB limit.

### M9 - Verification

Run before public launch:

- [ ] `npm run validate` passes on all records.
- [ ] The site builds and deploys to Pages without errors.
- [ ] Spot check: for 10 random published records, every figure matches its source snapshot word for word.
- [ ] Every Tier A estimate shows a range, a method version, and at least one cited assumption.
- [ ] Auto-merge test: a seeded Tier A change and a seeded LOW-confidence change both get `needs-review`. A seeded HIGH-confidence Tier C change gets `auto-ok`.
- [ ] Budget test: one full weekly cycle (collect, check, estimate, brief) costs under $6 in the run logs (illustrative, about a quarter of the monthly budget - confirm).
- [ ] Sign-up test: a submitted email shows up in the form service and does not appear anywhere in the repo or in the built site.
- [ ] Analytics records a test visit.
- [ ] Manual smoke test on phone width: table filters, map markers, a profile page, the overlap view and CSV download all work.
- [ ] Footer disclaimer, ODbL notice and links to the other trackers are present on every page.
- [ ] Every source enabled in a collector is marked `approved` in `docs/sources.md`.

## Out of scope / future additions

- Contractor/supplier directory for owner-side procurement leads. *Deferred.* Start a separate PRD once the site reaches about 100 weekly visitors, or once 5 procurement-lead conversations confirm demand. It should link to Source Louisiana rather than copy it.
- Low-carbon materials broker. *Deferred.* This needs its own PRD and a non-Pages host, because GitHub Pages doesn't allow online businesses or SaaS.
- Sending email (the weekly brief by email). *Deferred.* Start a PRD once 50+ sign-ups are collected (illustrative - confirm). Buttondown, Beehiiv and Substack were all considered.
- Paid tier, accounts or paywall. *Deliberate:* v1 is fully open.
- Reusing Louisiana AI Hub or LouisianAI data. *Deliberate:* their terms don't grant open reuse. We link to them instead. An optional reuse request to the AI Hub is a separate task.
- Other states or the wider Gulf Coast. *Deliberate:* Louisiana only.
- Engineering-grade quantity takeoffs. *Deliberate:* v1 estimates are indicative ranges only.
- Parked ideas from the handoff (deeptech landing pad, subcontractor working capital, workforce housing). *Deliberate:* not part of this track.

## Open questions to resolve during implementation

- Which parish agenda sources exist in machine-readable form, and which need PDF parsing? Resolve this in M1 and M3.
- Does LDEQ EDMS allow programmatic search, or only its web form? Choose the adapter approach in M3.
- Which map library and tile provider works within free terms on a static site (e.g. Leaflet with OSM tiles, following the tile usage policy)? Decide in M6.
- Geocoding approach for projects with only a parish or address. Decide in M6.
- Which LNG, ammonia and chemical projects make up the Tier A seed set? Decide in M2.

## Pre-mortem flags

**Technical risks:**

- The LLM extracts a wrong capex figure or parish and it auto-merges. Caught by M4: verbatim quote matching, auto-merge only at HIGH confidence below $1B, and headline changes always reviewed. M9 spot-checks this.
- The $10M threshold creates more candidates than the $25 budget can process. Caught by M8's cost guard and M9's budget test. The fallback is to raise the Tier C refresh interval.
- Source sites change layout, or throttle or block the collector. Caught by M8's change detection and failure alerts, and M1's rate limits.
- A source's terms forbid automated access. Caught by M1's terms gate. That source moves to `ask` or `blocked`.
- Scheduled workflows are disabled after 60 days without activity. Caught by the M8 keep-alive check.
- Benchmarks for material intensity can't be sourced for some project types. Caught in M5: estimates show "no estimate: no cited benchmark" rather than an invented value.
- Snapshots push the repo toward the 1 GB limit. Caught by the M2 size cap and the M8 repo size check.

**Strategic risks:**

- Nobody finds the site, so it misses 100 weekly visitors. The only distribution is the manual launch and LinkedIn in M7. Caught at the 3-month check in `docs/metrics.md`; if traffic is under about 30 weekly visitors at week 6, revisit distribution.
- Tier-2 suppliers want lead alerts and bid timing, not a dataset. That would lead to visits but no return visits. Watch the returning-visitor share in analytics; this also informs the phase-2 directory PRD.
- Wrong estimates hurt credibility with procurement leads. Mitigated by visible ranges, method versioning, review of Tier A and B, and the disclaimer copy (M5, M6).
- The success metric counts visitors, which doesn't prove broker demand. That is accepted for v1. The directory PRD should use a demand-side metric instead.

**Constraints check:** No milestone uses a Cocoon system. No real-world action (sending emails, posting, contacting sources) runs automatically; M1 source requests and M7 launch posts are drafts for Eliot to send. Email addresses stay in the form service.

## Research grounding

Checked 2026-09-30 by web search and by fetching each page. Market facts come from the handoff doc (29 Sept 2026), with sources listed there.

- GitHub Pages limits: published sites up to 1 GB, 100 GB/month soft bandwidth limit, 10-minute deploy timeout. It may not be used for online businesses, e-commerce or SaaS. Source: https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits
- GitHub Actions is free for standard GitHub-hosted runners in public repos. Source: https://docs.github.com/en/actions/reference/usage-limits-billing-and-administration
- Actions jobs can run up to 6 hours each. Source: https://docs.github.com/en/actions/reference/limits
- In a public repo, scheduled workflows are disabled automatically after 60 days with no repository activity. Source: https://docs.github.com/en/actions/how-tos/manage-workflow-runs/disable-and-enable-workflows
- Claude Haiku 4.5 costs $1/$5 per million input/output tokens, and Sonnet 5.5 costs $2/$10. The Batch API is 50% off. Source: https://platform.claude.com/docs/en/about-claude/pricing
- The LPSC Document Access Center gives public search of all public docket documents, with PDF and Excel export. The access guide doesn't mention terms for automated access. Source: https://lpsc.louisiana.gov/docs/general/LPSC-Online-Document-Access-Information.pdf
- LDEQ EDMS is a public repository of all official LDEQ records. The page doesn't state terms for automated access or reuse; the public records contact is publicrecords@la.gov. Source: https://www.deq.louisiana.gov/page/edms
- ITEP approvals are posted on the LED Board website after BC&I approval. The page doesn't say whether application details are public. Source: https://www.opportunitylouisiana.gov/incentive/industrial-tax-exemption/itep-2024
- ODbL requires attribution and share-alike for publicly used adapted databases, and doesn't prohibit commercial use. This is a human-readable summary, not the legal text. Source: https://opendatacommons.org/licenses/odbl/summary/

Not verified, so they appear as illustrative values or risks above: free-tier limits for the form service and analytics tool (M1); OSM tile usage terms (M6 open question); full terms of use for LED, LPSC, LDEQ and parish sites (M1 gate).
