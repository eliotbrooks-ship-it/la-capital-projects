#!/usr/bin/env python3
"""Compile data/ + site/ into dist/ (the static site GitHub Pages serves). Standard library only.

Environment variables (all optional):
  BASE                 URL path prefix, e.g. "/la-capital-projects/" for a Pages project site. Default "/".
  SIGNUP_FORM_URL      Form-service endpoint for the email sign-up. If unset, the form shows "opening soon".
  ANALYTICS_PROVIDER   "goatcounter" or "plausible". If unset, no analytics script is added.
  ANALYTICS_SITE_ID    GoatCounter code (e.g. "lacapital") or Plausible domain.
Usage: python3 scripts/build.py
"""
import csv
import datetime as dt
import html
import io
import json
import os
import pathlib
import shutil

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SITE = ROOT / "site"
DIST = ROOT / "dist"

BASE = os.environ.get("BASE", "/")
if not BASE.endswith("/"):
    BASE += "/"
SIGNUP_FORM_URL = os.environ.get("SIGNUP_FORM_URL", "").strip()
ANALYTICS_PROVIDER = os.environ.get("ANALYTICS_PROVIDER", "").strip().lower()
ANALYTICS_SITE_ID = os.environ.get("ANALYTICS_SITE_ID", "").strip()
METHOD_VERSION = "v0.1"

TYPE_LABELS = {
    "data_center": "Data center", "lng": "LNG", "chemicals": "Chemicals",
    "ammonia_hydrogen": "Ammonia / hydrogen", "steel_metals": "Steel / metals",
    "manufacturing": "Manufacturing", "spaceport_aerospace": "Spaceport / aerospace",
    "power_generation": "Power generation", "infrastructure": "Infrastructure", "other": "Other",
}
STATUS_LABELS = {
    "announced": "Announced", "permitting": "Permitting", "approved": "Approved",
    "under_construction": "Under construction", "operational": "Operational",
    "paused": "Paused", "cancelled": "Cancelled",
}
BASIS_LABELS = {"capex": "Stated investment", "financing": "Financing raised", "commitment": "Spending commitment"}

COMPLETION_BASIS = {"construction_complete": "construction complete", "first_operations": "first operations",
                    "full_operations": "full commercial operations"}
JOB_KINDS = {"permanent_direct": "Permanent direct", "permanent_indirect": "Permanent indirect",
             "permanent_total": "Permanent total", "construction_peak": "Construction (peak on site)",
             "construction_total": "Construction (total over build)"}
ROLE_LABELS = {"epc": "EPC contractor", "engineering_procurement": "Engineering and procurement",
               "general_contractor": "General contractor", "technology_licensor": "Technology licensor",
               "equipment_supplier": "Equipment supplier", "civil_works": "Civil works", "services": "Services",
               "other": "Other"}
MAIN_ROLES = ("epc", "general_contractor", "engineering_procurement")

e = html.escape


def jobs_of(p):
    return {j["kind"]: j for j in p.get("jobs", [])}


def permanent_jobs(p):
    """Best single permanent-jobs figure for the table: total if stated, else direct."""
    j = jobs_of(p)
    return j.get("permanent_total") or j.get("permanent_direct")


def fmt_date(v):
    """'2029-H2' -> 'H2 2029'; other formats unchanged."""
    if v and len(v) == 7 and v[5] == "H":
        return f"{v[5:]} {v[:4]}"
    return v


SHORT_BASIS = {"construction_complete": "build complete", "first_operations": "ops start", "full_operations": "full ops"}


def completion_cell(p):
    ec = p.get("expected_completion")
    if not ec:
        return "—"
    return f'{e(fmt_date(ec["value"]))}<div class="muted small">{SHORT_BASIS[ec["basis"]]}</div>'


def contractor_cell(p):
    names = main_contractors(p)
    if not names:
        return "—"
    return e(names[0]) + (f' <span class="muted small">+{len(names) - 1} more</span>' if len(names) > 1 else "")


def jobs_cell(p):
    j = permanent_jobs(p)
    return f'{j["value"]:,}' if j else "—"


def main_contractors(p):
    return [c["name"] for c in p.get("contractors", []) if c["role"] in MAIN_ROLES]


def load(name):
    return [json.loads(f.read_text()) for f in sorted((DATA / name).glob("*.json"))]


def usd(v):
    if v >= 1e9:
        s = f"{v / 1e9:.1f}".rstrip("0").rstrip(".")
        return f"${s}B"
    return f"${v / 1e6:,.0f}M"


def month_index(value, is_end):
    """'2027' / '2027-H2' / '2027-05' / '2027-05-04' -> months since year 0."""
    if not value:
        return None
    y = int(value[:4])
    rest = value[5:]
    if not rest:
        m = 12 if is_end else 1
    elif rest.startswith("H"):
        m = (6 if rest == "H1" else 12) if is_end else (1 if rest == "H1" else 7)
    else:
        m = int(rest[:2])
    return y * 12 + (m - 1)


def page(title, body, *, description="", active=""):
    nav = [("", "Home"), ("projects/", "Projects"), ("map/", "Map"), ("overlap/", "Parish overlap"),
           ("briefs/", "Briefs"), ("methodology/", "Methodology"), ("sources/", "Sources")]
    current = ' aria-current="page"'
    links = "".join(
        f'<a href="{BASE}{href}"{current if href == active else ""}>{label}</a>' for href, label in nav)
    analytics = ""
    if ANALYTICS_PROVIDER == "goatcounter" and ANALYTICS_SITE_ID:
        analytics = (f'<script data-goatcounter="https://{e(ANALYTICS_SITE_ID)}.goatcounter.com/count" '
                     'async src="//gc.zgo.at/count.js"></script>')
    elif ANALYTICS_PROVIDER == "plausible" and ANALYTICS_SITE_ID:
        analytics = f'<script defer data-domain="{e(ANALYTICS_SITE_ID)}" src="https://plausible.io/js/script.js"></script>'
    full_title = "Louisiana Capital Projects Tracker" if not title else f"{title} · Louisiana Capital Projects Tracker"
    desc = description or "Open data on every Louisiana capital project over $10M: what's being built, where, when, and what it needs."
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(full_title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="stylesheet" href="{BASE}assets/app.css">
<link rel="alternate" type="application/rss+xml" title="Weekly briefs" href="{BASE}briefs/feed.xml">
{analytics}
</head>
<body>
<header class="site-header">
  <a class="brand" href="{BASE}">LA Capital Projects</a>
  <nav>{links}</nav>
</header>
<main>
{body}
</main>
<footer class="site-footer">
  <p>Data licensed <a href="https://opendatacommons.org/licenses/odbl/1-0/">ODbL 1.0</a>. Independent personal project; not affiliated with any employer, agency or project owner. Estimates are indicative, not engineering quantities.</p>
  <p>For deeper data-center coverage see <a href="https://louisianaaihub.com/">Louisiana AI Hub</a> and <a href="https://louisianai.com/">LouisianAI</a>. Downloads: <a href="{BASE}data/projects.csv">CSV</a> · <a href="{BASE}data/projects.json">JSON</a> · <a href="{BASE}data/projects.geojson">GeoJSON</a></p>
</footer>
</body>
</html>
"""


def signup_block():
    intro = ("<h2>Get the weekly brief</h2><p>Get the weekly Louisiana capital projects brief. "
             "Leave your email and we'll let you know when email delivery starts. We only use it for the brief.</p>")
    if SIGNUP_FORM_URL:
        form = (f'<form class="signup" action="{e(SIGNUP_FORM_URL)}" method="POST">'
                '<label for="email" class="sr-only">Email</label>'
                '<input id="email" name="email" type="email" required placeholder="you@company.com" autocomplete="email">'
                '<button type="submit">Sign up</button></form>')
    else:
        form = '<p class="muted">Sign-up opens soon.</p>'
    return f'<section class="card signup-card">{intro}{form}</section>'


def build():
    projects = load("projects")
    sources = {s["id"]: s for s in load("sources")}
    estimates = {x["id"]: x for x in load("estimates")}
    built = dt.date.today().isoformat()

    if DIST.exists():
        shutil.rmtree(DIST)
    shutil.copytree(SITE, DIST)
    (DIST / "data").mkdir(exist_ok=True)

    # ---- data downloads
    public = []
    for p in projects:
        q = dict(p)
        q["type_label"] = TYPE_LABELS[p["type"]]
        q["status_label"] = STATUS_LABELS[p["status"]]
        q["headline_capex_label"] = usd(p["headline_capex_usd"])
        q["url"] = f"{BASE}projects/{p['id']}/"
        public.append(q)
    meta = {"generated": built, "license": "ODbL-1.0", "method_version": METHOD_VERSION, "count": len(projects)}
    (DIST / "data" / "projects.json").write_text(json.dumps({"meta": meta, "projects": public}, indent=1))
    (DIST / "data" / "sources.json").write_text(json.dumps(list(sources.values()), indent=1))

    buf = io.StringIO()
    cols = ["id", "name", "owner_company", "type", "parish", "status", "headline_capex_usd", "tier",
            "expected_completion", "expected_completion_basis"] + [f"jobs_{k}" for k in JOB_KINDS] + [
            "contractors", "site_acres", "permits", "itep_application_number", "itep_approved_date",
            "procurement_urls", "confidence", "lat", "lon", "location_precision", "last_verified", "source_urls"]
    w = csv.writer(buf)
    w.writerow(cols)
    for p in projects:
        ec, jb, itep = p.get("expected_completion") or {}, jobs_of(p), p.get("itep") or {}
        row = {c: p.get(c, "") for c in cols}
        row.update({
            "expected_completion": ec.get("value", ""), "expected_completion_basis": ec.get("basis", ""),
            "contractors": "; ".join(f'{c["name"]} ({c["role"]})' for c in p.get("contractors", [])),
            "site_acres": (p.get("site_acres") or {}).get("value", ""),
            "permits": "; ".join(f'{x["agency"]} {x["number"]}' for x in p.get("permits", [])),
            "itep_application_number": itep.get("application_number", ""),
            "itep_approved_date": itep.get("approved_date") or "",
            "procurement_urls": " ".join(x["url"] for x in p.get("procurement_links", [])),
            "source_urls": " ".join(sources[s]["url"] for s in p["source_ids"]),
        })
        row.update({f"jobs_{k}": jb[k]["value"] if k in jb else "" for k in JOB_KINDS})
        w.writerow([row[c] for c in cols])
    (DIST / "data" / "projects.csv").write_text(buf.getvalue())

    features = [{"type": "Feature",
                 "geometry": {"type": "Point", "coordinates": [p["lon"], p["lat"]]},
                 "properties": {"id": p["id"], "name": p["name"], "type": p["type"], "parish": p["parish"],
                                "status": p["status"], "headline_capex_usd": p["headline_capex_usd"],
                                "location_precision": p.get("location_precision", "approximate")}}
                for p in projects if p.get("lat") is not None]
    (DIST / "data" / "projects.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": features}))

    # ---- home
    total = sum(p["headline_capex_usd"] for p in projects)
    parishes = sorted({p["parish"] for p in projects})
    building = sum(1 for p in projects if p["status"] == "under_construction")
    home = f"""
<section class="hero">
  <h1>Every Louisiana capital project over $10M: what's being built, where, when, and what it needs.</h1>
  <p class="lede">Open data. Sources on every figure. Material estimates shown with their assumptions.</p>
  <p class="cta"><a class="button" href="{BASE}projects/">Browse projects</a> <a class="button ghost" href="{BASE}map/">See the map</a></p>
</section>
<section class="stats" aria-label="Summary">
  <div class="stat"><span class="val">{len(projects)}</span><span class="lbl">projects tracked</span></div>
  <div class="stat"><span class="val">{usd(total)}</span><span class="lbl">headline value</span></div>
  <div class="stat"><span class="val">{building}</span><span class="lbl">under construction</span></div>
  <div class="stat"><span class="val">{len(parishes)}</span><span class="lbl">parishes</span></div>
</section>
<p class="muted small">Early preview: seed records only, entered by hand on {e(min(p['first_seen'] for p in projects))}. Headline value sums each project's headline figure, which may be investment, financing or commitments; see each project for the basis.</p>
{signup_block()}
"""
    (DIST / "index.html").write_text(page("", home, active=""))

    # ---- projects table (client-side filtering in assets/table.js)
    type_opts = "".join(f'<option value="{k}">{v}</option>' for k, v in TYPE_LABELS.items())
    status_opts = "".join(f'<option value="{k}">{v}</option>' for k, v in STATUS_LABELS.items())
    parish_opts = "".join(f'<option>{e(x)}</option>' for x in parishes)
    rows = "".join(
        f'<tr data-type="{p["type"]}" data-parish="{e(p["parish"])}" data-status="{p["status"]}" data-tier="{p["tier"]}" '
        f'data-confidence="{p["confidence"]}" data-capex="{p["headline_capex_usd"]}">'
        f'<td><a href="{BASE}projects/{p["id"]}/">{e(p["name"])}</a><div class="muted small">{e(p["owner_company"])}</div></td>'
        f'<td>{TYPE_LABELS[p["type"]]}</td><td>{e(p["parish"])}</td><td>{STATUS_LABELS[p["status"]]}</td>'
        f'<td class="num" data-sort="{p["headline_capex_usd"]}">{usd(p["headline_capex_usd"])}</td>'
        f'<td data-sort="{month_index((p.get("expected_completion") or {}).get("value"), False) or 999999}">{completion_cell(p)}</td>'
        f'<td class="num" data-sort="{(permanent_jobs(p) or {}).get("value", -1)}">{jobs_cell(p)}</td>'
        f'<td>{contractor_cell(p)}</td>'
        f'<td>{p["tier"]}</td><td><span class="conf conf-{p["confidence"].lower()}">{p["confidence"]}</span></td></tr>'
        for p in sorted(projects, key=lambda x: -x["headline_capex_usd"]))
    table = f"""
<h1>Projects</h1>
<form class="filters" id="filters" aria-label="Filter projects">
  <label>Type <select name="type"><option value="">All</option>{type_opts}</select></label>
  <label>Parish <select name="parish"><option value="">All</option>{parish_opts}</select></label>
  <label>Status <select name="status"><option value="">All</option>{status_opts}</select></label>
  <label>Tier <select name="tier"><option value="">All</option><option value="A">A ($1B+)</option><option value="B">B ($100M–$1B)</option><option value="C">C ($10M–$100M)</option></select></label>
  <label>Min value <select name="min"><option value="0">Any</option><option value="100000000">$100M+</option><option value="1000000000">$1B+</option><option value="10000000000">$10B+</option></select></label>
  <label>Confidence <select name="confidence"><option value="">All</option><option>HIGH</option><option>MEDIUM</option><option>LOW</option></select></label>
</form>
<p class="muted small"><span id="count">{len(projects)}</span> shown · <a href="#" id="dl-csv">Download CSV of current filter</a> · <a href="{BASE}data/projects.json">Full JSON</a></p>
<div class="table-wrap">
<table id="projects" class="data">
<thead><tr><th data-key="name">Project</th><th>Type</th><th>Parish</th><th>Status</th><th data-key="capex" class="num">Value</th><th data-key="completion">Expected completion</th><th data-key="jobs" class="num">Permanent jobs</th><th>Main contractor</th><th>Tier</th><th>Confidence</th></tr></thead>
<tbody>{rows}</tbody>
</table>
</div>
<script src="{BASE}assets/table.js" defer></script>
"""
    (DIST / "projects").mkdir(exist_ok=True)
    (DIST / "projects" / "index.html").write_text(page("Projects", table, active="projects/"))

    # ---- profile pages
    for p in projects:
        used = []

        def cite(sid):
            if sid not in used:
                used.append(sid)
            n = used.index(sid) + 1
            return f'<sup><a href="#src-{n}">[{n}]</a></sup>'

        capex_rows = "".join(
            f'<tr><td class="num">{usd(c["value_usd"])}</td><td>{BASIS_LABELS[c["basis"]]}</td><td>{e(c["as_of"])}</td>'
            f'<td>{e(c.get("note", ""))}{cite(c["source_id"])}</td></tr>' for c in p["capex_values"])
        phases = ""
        for ph in p["phases"]:
            span = e(fmt_date(ph["start"]) or "?") + ("" if ph["name"] == "operations" else f' → {e(fmt_date(ph.get("end")) or "?")}')
            badge = ' <span class="badge">includes estimated dates</span>' if ph.get("estimated") else ""
            c = cite(ph["source_id"]) if ph.get("source_id") else ""
            phases += f'<li><strong>{ph["name"].capitalize()}</strong>: {span}{c}{badge}<div class="muted small">{e(ph.get("note", ""))}</div></li>'
        facts = [("Owner", e(p["owner_company"])), ("Type", TYPE_LABELS[p["type"]]),
                 ("Parish", e(p["parish"])),
                 ("Status", STATUS_LABELS[p["status"]] + cite(p["status_source_id"])),
                 ("Headline value", usd(p["headline_capex_usd"]) + f' (tier {p["tier"]})')]
        if p.get("capacity"):
            c = p["capacity"]
            facts.append(("Capacity", f'{c["value"]:,} {e(c["unit"])}{cite(c["source_id"])}'))
        ec = p.get("expected_completion")
        facts.append(("Expected completion",
                      f'{e(fmt_date(ec["value"]))} ({COMPLETION_BASIS[ec["basis"]]}){cite(ec["source_id"])}'
                      + (f'<div class="muted small">{e(ec["note"])}</div>' if ec.get("note") else "") if ec else '<span class="muted">Not stated</span>'))
        if p.get("site_acres"):
            a = p["site_acres"]
            facts.append(("Site area", f'{a["value"]:,.0f} acres{cite(a["source_id"])}'
                          + (f'<div class="muted small">{e(a["note"])}</div>' if a.get("note") else "")))
        facts.append(("Location", e(p.get("location_note", "")) +
                      (' <span class="badge">approximate</span>' if p.get("location_precision") != "exact" else "")))
        facts.append(("Confidence", f'<span class="conf conf-{p["confidence"].lower()}">{p["confidence"]}</span>'))
        facts.append(("Last verified", e(p["last_verified"])))
        fact_html = "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in facts)

        none = '<p class="muted">None found in public sources yet.</p>'
        jb = p.get("jobs", [])
        jobs_html = ('<div class="table-wrap"><table class="data"><tbody>' + "".join(
            f'<tr><td>{JOB_KINDS[j["kind"]]}</td><td class="num">{j["value"]:,}{cite(j["source_id"])}</td>'
            f'<td class="muted small">{e(j.get("note", ""))}</td></tr>'
            for j in sorted(jb, key=lambda j: list(JOB_KINDS).index(j["kind"]))) + '</tbody></table></div>') if jb else none
        cs = p.get("contractors", [])
        con_html = ('<div class="table-wrap"><table class="data"><tbody>' + "".join(
            f'<tr><td><strong>{e(c["name"])}</strong>{cite(c["source_id"])}<div class="muted small">{e(c.get("note", ""))}</div></td>'
            f'<td>{ROLE_LABELS[c["role"]]}</td></tr>'
            for c in sorted(cs, key=lambda c: list(ROLE_LABELS).index(c["role"]))) + '</tbody></table></div>') if cs else none
        pm = p.get("permits", [])
        permit_html = ('<div class="table-wrap"><table class="data"><thead><tr><th>Agency</th><th>Type</th><th>Number</th><th>Date</th></tr></thead><tbody>' + "".join(
            f'<tr><td>{e(x["agency"])}</td><td>{e(x["type"])}' + (f' <span class="badge">{e(x["status"])}</span>' if x.get("status") else "")
            + (f'<div class="muted small">{e(x["note"])}</div>' if x.get("note") else "")
            + f'</td><td>{e(x["number"])}{cite(x["source_id"])}</td><td>{e(x.get("date") or "")}</td></tr>' for x in pm)
            + '</tbody></table></div>') if pm else none
        itep = p.get("itep")
        itep_html = (f'<p><strong>Industrial Tax Exemption (ITEP):</strong> application {e(itep["application_number"])}'
                     + (f', approved {e(itep["approved_date"])}' if itep.get("approved_date") else "") + f'{cite(itep["source_id"])}</p>'
                     if itep else '<p class="muted small">Industrial Tax Exemption (ITEP): no application number found yet.</p>')
        links = p.get("procurement_links", [])
        proc_html = ("<ul>" + "".join(
            f'<li><a href="{e(x["url"])}" rel="noopener">{e(x["label"])}</a>{cite(x["source_id"]) if x.get("source_id") else ""}</li>'
            for x in links) + "</ul>") if links else none
        extra_html = f"""
<div class="grid2">
  <section class="card"><h2>Expected jobs</h2>{jobs_html}</section>
  <section class="card"><h2>Contractors and suppliers</h2>{con_html}</section>
</div>
<div class="grid2">
  <section class="card"><h2>Permits and approvals</h2>{permit_html}{itep_html}</section>
  <section class="card"><h2>Selling to this project</h2>{proc_html}<p class="muted small">Company-level vendor pages only.</p></section>
</div>"""
        est = estimates.get(p.get("estimate_id") or "")
        if est:
            r = lambda k: f'{est[k]["low"]:,.0f} – {est[k]["likely"]:,.0f} – {est[k]["high"]:,.0f}'
            est_html = (f'<table class="data"><thead><tr><th>Material</th><th class="num">Low – likely – high</th></tr></thead>'
                        f'<tbody><tr><td>Concrete (m³)</td><td class="num">{r("concrete_m3")}</td></tr>'
                        f'<tr><td>Steel (t)</td><td class="num">{r("steel_t")}</td></tr></tbody></table>'
                        f'<p class="badge">Estimate · method {e(est["method_version"])} · <a href="{BASE}methodology/">How we estimate</a></p>')
        else:
            est_html = (f'<p class="muted">No materials estimate yet. Estimates are being built under method {METHOD_VERSION}; '
                        f'<a href="{BASE}methodology/">how we estimate</a>.</p>')

        src_list = ""
        for i, sid in enumerate(used, 1):
            s = sources[sid]
            kind = "primary" if s.get("primary") else "secondary"
            qv = "" if s.get("quote_verified") else ' <span class="badge warn">quote not yet re-verified</span>'
            quotes = "".join(f"<blockquote>{e(q)}</blockquote>" for q in s["quotes"])
            src_list += (f'<li id="src-{i}"><a href="{e(s["url"])}" rel="noopener">{e(s["publisher"])}</a>'
                         f' · {e(s.get("published") or "undated")} · {kind}{qv}<details><summary>Quoted text</summary>{quotes}</details></li>')
        notes = f'<p class="note">{e(p["notes"])}</p>' if p.get("notes") else ""
        body = f"""
<p class="crumbs"><a href="{BASE}projects/">Projects</a> / {e(p["name"])}</p>
<h1>{e(p["name"])}</h1>
{notes}
<div class="grid2">
  <section class="card"><h2>Facts</h2><dl class="facts">{fact_html}</dl></section>
  <section class="card"><h2>Timeline</h2><ul class="timeline">{phases}</ul></section>
</div>
<section class="card"><h2>Reported value</h2>
<p class="muted small">Every sourced figure is listed. The headline is the most recent primary-source figure.</p>
<div class="table-wrap"><table class="data"><thead><tr><th class="num">Value</th><th>Basis</th><th>As of</th><th>Note</th></tr></thead><tbody>{capex_rows}</tbody></table></div>
</section>
{extra_html}
<section class="card"><h2>Materials</h2>{est_html}</section>
<section class="card"><h2>Sources</h2><ol class="sources">{src_list}</ol></section>
"""
        d = DIST / "projects" / p["id"]
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(page(p["name"], body, active="projects/",
                                           description=f'{p["name"]}, {p["parish"]} Parish: sources, timeline and materials.'))

    # ---- map
    map_body = f"""
<h1>Map</h1>
<p class="muted small">Marker positions are approximate unless a project says otherwise. Click a marker for the project.</p>
<link rel="stylesheet" href="{BASE}vendor/leaflet/leaflet.css">
<div id="map" class="map" role="region" aria-label="Map of projects"></div>
<ul class="legend" id="legend"></ul>
<script src="{BASE}vendor/leaflet/leaflet.js" defer></script>
<script>window.LACP_BASE = {json.dumps(BASE)}; window.LACP_TYPES = {json.dumps(TYPE_LABELS)};</script>
<script src="{BASE}assets/map.js" defer></script>
"""
    (DIST / "map").mkdir(exist_ok=True)
    (DIST / "map" / "index.html").write_text(page("Map", map_body, active="map/"))

    # ---- parish overlap (construction phase by quarter)
    windows = []
    for p in projects:
        for ph in p["phases"]:
            if ph["name"] != "construction":
                continue
            s, en = month_index(ph["start"], False), month_index(ph.get("end"), True)
            if s is None or en is None:
                continue
            windows.append((p, s, en, bool(ph.get("estimated"))))
    if windows:
        q0 = min(w[1] for w in windows) // 3
        q1 = max(w[2] for w in windows) // 3
        quarters = list(range(q0, q1 + 1))
        by_parish = {}
        for p, s, en, est_flag in windows:
            by_parish.setdefault(p["parish"], []).append((p, s // 3, en // 3, est_flag))
        max_n = 1
        cells = {}
        for parish, ws in by_parish.items():
            for q in quarters:
                active = [(p, f) for p, a, b, f in ws if a <= q <= b]
                cells[(parish, q)] = active
                max_n = max(max_n, len(active))
        head = "".join(
            f'<th scope="col" class="q">{(q // 4)}<br>Q{q % 4 + 1}</th>' if q % 4 == 0 else f'<th scope="col" class="q">Q{q % 4 + 1}</th>'
            for q in quarters)
        body_rows = ""
        for parish in sorted(by_parish, key=lambda x: -sum(len(cells[(x, q)]) for q in quarters)):
            tds = ""
            for q in quarters:
                act = cells[(parish, q)]
                if not act:
                    tds += '<td class="cell"></td>'
                    continue
                n = len(act)
                wf = sum(jobs_of(p)["construction_peak"]["value"] for p, _ in act if "construction_peak" in jobs_of(p))
                est_cls = " est" if any(f for _, f in act) else ""
                names = "; ".join(p["name"] for p, _ in act)
                label = f"{parish}, {q // 4} Q{q % 4 + 1}: {n} project(s) in construction: {names}" + (f"; sourced peak workforce {wf:,}" if wf else "")
                tds += f'<td class="cell lvl{min(3, n)}{est_cls}" title="{e(label)}"><span class="sr-only">{e(label)}</span>{n}</td>'
            body_rows += f'<tr><th scope="row">{e(parish)}</th>{tds}</tr>'
        grid = f'<div class="table-wrap"><table class="heat"><thead><tr><th></th>{head}</tr></thead><tbody>{body_rows}</tbody></table></div>'
    else:
        grid = '<p class="muted">No construction windows yet.</p>'
    overlap = f"""
<h1>Parish overlap</h1>
<p>How many tracked projects are in construction in each parish, by quarter. Overlaps show where demand for crews, concrete, steel and housing stacks up.</p>
<p class="muted small">Numbers are project counts. Hatched cells include at least one estimated date (for example, a construction end inferred from a first-production target). Hover or tap a cell for project names and any sourced peak workforce.</p>
{grid}
"""
    (DIST / "overlap").mkdir(exist_ok=True)
    (DIST / "overlap" / "index.html").write_text(page("Parish overlap", overlap, active="overlap/"))

    # ---- methodology
    methodology = f"""
<h1>Methodology <span class="badge">{METHOD_VERSION}</span></h1>
<section class="card"><h2>What's included</h2>
<p>Capital projects in Louisiana with a publicly reported value of $10M or more: data centers, LNG, chemicals, ammonia and hydrogen, steel and metals, manufacturing, the spaceport, power and infrastructure.</p></section>
<section class="card"><h2>Tiers</h2>
<ul><li><strong>Tier A</strong> ($1B+): full profile. Materials estimated bottom-up from public filings, checked against benchmarks, shown as a low / likely / high range, reviewed by a person.</li>
<li><strong>Tier B</strong> ($100M–$1B): formula estimate refined with facts from permits, reviewed by a person.</li>
<li><strong>Tier C</strong> ($10M–$100M): basic record with a formula estimate per $M of value.</li></ul></section>
<section class="card"><h2>Headline value</h2>
<p>We list every sourced figure. The headline is the most recent figure from a primary source (government or company). Each figure is labelled as a stated investment, financing raised, or a spending commitment, because these are not the same thing.</p></section>
<section class="card"><h2>Confidence</h2>
<ul><li><strong>HIGH</strong>: value, parish and status each come from a primary government or company document.</li>
<li><strong>MEDIUM</strong>: at least one of these comes only from news, or the value is financing rather than stated investment.</li>
<li><strong>LOW</strong>: partial or inferred.</li></ul>
<p>Map positions are approximate unless marked otherwise.</p></section>
<section class="card"><h2>Materials estimates</h2>
<p>Not yet published. Every estimate will show its method version, its assumptions and a source or benchmark for each assumption. We will not publish a benchmark we can't cite. Estimates are indicative ranges, not engineering quantities.</p></section>
<section class="card"><h2>Limitations</h2>
<p>Announced values often change, and some projects never proceed. Dates marked as estimated are inferred. Nothing here is investment, legal or engineering advice.</p></section>
"""
    (DIST / "methodology").mkdir(exist_ok=True)
    (DIST / "methodology" / "index.html").write_text(page("Methodology", methodology, active="methodology/"))

    # ---- sources
    src_rows = "".join(
        f'<tr><td><a href="{e(s["url"])}" rel="noopener">{e(s["publisher"])}</a></td><td>{e(s["doc_type"].replace("_", " "))}</td>'
        f'<td>{e(s.get("published") or "undated")}</td><td>{"primary" if s.get("primary") else "secondary"}</td></tr>'
        for s in sorted(sources.values(), key=lambda s: s.get("published") or "", reverse=True))
    sources_body = f"""
<h1>Sources</h1>
<p>Every figure on this site links to one of these documents. We collect only from public sources whose terms allow it, and we link to other trackers rather than copying their data.</p>
<div class="table-wrap"><table class="data"><thead><tr><th>Publisher</th><th>Type</th><th>Published</th><th>Kind</th></tr></thead><tbody>{src_rows}</tbody></table></div>
"""
    (DIST / "sources").mkdir(exist_ok=True)
    (DIST / "sources" / "index.html").write_text(page("Sources", sources_body, active="sources/"))

    # ---- briefs (placeholder archive + RSS)
    briefs = sorted((SITE / "briefs").glob("*.html"), reverse=True)
    items = "".join(f'<li><a href="{BASE}briefs/{b.name}">{b.stem}</a></li>' for b in briefs)
    briefs_body = f"""
<h1>Weekly briefs</h1>
{'<ul>' + items + '</ul>' if items else '<p class="muted">The first brief will appear here after launch.</p>'}
<p class="small"><a href="{BASE}briefs/feed.xml">RSS feed</a></p>
{signup_block()}
"""
    (DIST / "briefs" / "index.html").write_text(page("Weekly briefs", briefs_body, active="briefs/"))
    rss_items = "".join(f"<item><title>Brief {b.stem}</title><link>{BASE}briefs/{b.name}</link></item>" for b in briefs)
    (DIST / "briefs" / "feed.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>Louisiana Capital Projects: weekly briefs</title>'
        f'<link>{BASE}briefs/</link><description>Weekly updates on Louisiana capital projects over $10M.</description>{rss_items}</channel></rss>')

    (DIST / ".nojekyll").write_text("")
    print(f"Built {len(projects)} project pages into {DIST.relative_to(ROOT)}/ (BASE={BASE})")


if __name__ == "__main__":
    build()
