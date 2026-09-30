#!/usr/bin/env python3
"""Validate every record under data/. Standard library only.

Checks required fields, enums, id format, tier consistency with headline capex,
the $10M threshold, and that every source_id resolves. Exits non-zero on any error.
Usage: python3 scripts/validate.py
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SCHEMA = DATA / "schema"
THRESHOLD_USD = 10_000_000
DATE_RE = re.compile(r"^\d{4}(-\d{2}(-\d{2})?|-H[12])?$")
ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def load_schema(name):
    return json.loads((SCHEMA / name).read_text())


def tier_for(usd):
    if usd >= 1_000_000_000:
        return "A"
    if usd >= 100_000_000:
        return "B"
    return "C"


def main():
    errors = []
    project_schema = load_schema("project.schema.json")
    source_schema = load_schema("source.schema.json")
    estimate_schema = load_schema("estimate.schema.json")

    def err(path, msg):
        errors.append(f"{path.relative_to(ROOT)}: {msg}")

    def load_dir(name):
        out = {}
        for f in sorted((DATA / name).glob("*.json")):
            try:
                rec = json.loads(f.read_text())
            except json.JSONDecodeError as e:
                err(f, f"invalid JSON ({e})")
                continue
            if f.stem != rec.get("id"):
                err(f, f"filename must equal id ({rec.get('id')!r})")
            out[rec.get("id")] = (f, rec)
        return out

    sources = load_dir("sources")
    projects = load_dir("projects")
    estimates = load_dir("estimates")

    def check_required(f, rec, schema):
        for k in schema["required"]:
            if k not in rec:
                err(f, f"missing required field '{k}'")
        if schema.get("additionalProperties") is False:
            for k in rec:
                if k not in schema["properties"]:
                    err(f, f"unknown field '{k}'")

    # Sources
    doc_types = set(source_schema["properties"]["doc_type"]["enum"])
    terms = set(source_schema["properties"]["terms_status"]["enum"])
    for sid, (f, s) in sources.items():
        check_required(f, s, source_schema)
        if not re.match(source_schema["properties"]["id"]["pattern"], sid or ""):
            err(f, "id must look like src-<slug>")
        if s.get("doc_type") not in doc_types:
            err(f, f"bad doc_type {s.get('doc_type')!r}")
        if s.get("terms_status") not in terms:
            err(f, f"bad terms_status {s.get('terms_status')!r}")
        if s.get("terms_status") == "blocked":
            err(f, "source is marked blocked in docs/sources.md and must not be used")
        if not str(s.get("url", "")).startswith("https://"):
            err(f, "url must be https")
        if not s.get("quotes"):
            err(f, "needs at least one quote")
        if s.get("snapshot_path") and not (DATA / "snapshots" / s["snapshot_path"]).exists():
            err(f, f"snapshot_path not found: {s['snapshot_path']}")

    def ref(f, sid, where):
        if sid not in sources:
            err(f, f"{where}: source_id {sid!r} does not resolve")

    # Projects
    types = set(project_schema["properties"]["type"]["enum"])
    statuses = set(project_schema["properties"]["status"]["enum"])
    confidences = set(project_schema["properties"]["confidence"]["enum"])
    bases = set(project_schema["properties"]["capex_values"]["items"]["properties"]["basis"]["enum"])
    phase_names = set(project_schema["properties"]["phases"]["items"]["properties"]["name"]["enum"])
    for pid, (f, p) in projects.items():
        check_required(f, p, project_schema)
        if not ID_RE.match(pid or ""):
            err(f, "id must be a lowercase slug")
        if p.get("type") not in types:
            err(f, f"bad type {p.get('type')!r}")
        if p.get("status") not in statuses:
            err(f, f"bad status {p.get('status')!r}")
        if p.get("confidence") not in confidences:
            err(f, f"bad confidence {p.get('confidence')!r}")
        head = p.get("headline_capex_usd", 0)
        if head < THRESHOLD_USD:
            err(f, f"headline capex {head} is below the ${THRESHOLD_USD:,} threshold")
        if p.get("tier") != tier_for(head):
            err(f, f"tier {p.get('tier')} does not match headline capex (expected {tier_for(head)})")
        values = [c.get("value_usd") for c in p.get("capex_values", [])]
        if head not in values:
            err(f, "headline_capex_usd must equal one of capex_values")
        for c in p.get("capex_values", []):
            if c.get("basis") not in bases:
                err(f, f"bad capex basis {c.get('basis')!r}")
            if not DATE_RE.match(str(c.get("as_of", ""))):
                err(f, f"bad as_of {c.get('as_of')!r}")
            ref(f, c.get("source_id"), "capex_values")
        ref(f, p.get("status_source_id"), "status_source_id")
        for ph in p.get("phases", []):
            if ph.get("name") not in phase_names:
                err(f, f"bad phase name {ph.get('name')!r}")
            for k in ("start", "end"):
                v = ph.get(k)
                if v is not None and not DATE_RE.match(v):
                    err(f, f"bad phase {k} {v!r}")
            if ph.get("source_id"):
                ref(f, ph["source_id"], "phases")
            elif not ph.get("estimated"):
                err(f, "a phase without source_id must be marked estimated")
        for k in ("capacity", "peak_workforce"):
            if p.get(k):
                ref(f, p[k].get("source_id"), k)
        for sid in p.get("source_ids", []):
            ref(f, sid, "source_ids")
        lat, lon = p.get("lat"), p.get("lon")
        if lat is not None and not (28.5 <= lat <= 33.1 and -94.1 <= lon <= -88.8):
            err(f, "lat/lon is outside Louisiana's bounding box")
        if p.get("estimate_id") and p["estimate_id"] not in estimates:
            err(f, f"estimate_id {p['estimate_id']!r} does not resolve")

    # Estimates
    for eid, (f, e) in estimates.items():
        check_required(f, e, estimate_schema)
        if e.get("project_id") not in projects:
            err(f, f"project_id {e.get('project_id')!r} does not resolve")
        for k in ("concrete_m3", "steel_t"):
            r = e.get(k, {})
            if not (r.get("low", 0) <= r.get("likely", 0) <= r.get("high", 0)):
                err(f, f"{k} must satisfy low <= likely <= high")

    if errors:
        print(f"FAIL: {len(errors)} problem(s)")
        for e in errors:
            print("  -", e)
        sys.exit(1)
    print(f"OK: {len(projects)} projects, {len(sources)} sources, {len(estimates)} estimates")


if __name__ == "__main__":
    main()
