#!/usr/bin/env python3
"""M3 collector: list new documents from approved sources, extract candidate projects with Claude, write them for review.

Writes (all under data/):
  candidates/<run-date>/<doc-slug>.json   one file per document that produced >= 1 candidate
  snapshots/<doc-slug>.txt                the text Claude saw (quotes are checked against this)
  review/unknown-capex.json               projects found without a stated value (appended)
  runs/<run-date>.json                    run log: counts, failures, tokens, cost
  runs/state.json                         documents already processed (so they aren't re-read)

Nothing here edits data/projects/. Candidates are merged by the Checker (M4) or by hand.

Usage:
  python3 -m pipeline.collect [--since 2025-01-01] [--max-docs 40] [--budget 1.50] [--sources led_news,cameron] [--dry-run]
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import sys

from .extract import BudgetExceeded, ClaudeClient, extract
from .fetch import Fetcher
from .sources import ADAPTERS, loader_for

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SNAPSHOT_MAX_BYTES = 2 * 1024 * 1024
MAX_ATTEMPTS = 3  # give up on a document after this many failed runs
DEFAULT_SINCE = "2025-01-01"


def slug_for(item):
    base = re.sub(r"[^a-z0-9]+", "-", (item.get("title") or item["url"]).lower()).strip("-")[:60] or "doc"
    digest = hashlib.sha1(item["key"].encode()).hexdigest()[:8]
    return f"{item['source']}-{base}-{digest}"


def load_json(path, default):
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def run(args, fetcher=None, client=None, today=None, data_dir=DATA):
    today = today or dt.date.today().isoformat()
    fetcher = fetcher or Fetcher()
    client = client or ClaudeClient(budget_usd=args.budget)
    state_path = data_dir / "runs" / "state.json"
    state = load_json(state_path, {"seen": {}})
    state.setdefault("seen", {})
    state.setdefault("failed", {})
    existing = [load_json(f, {}) for f in sorted((data_dir / "projects").glob("*.json"))]
    sources = [s for s in args.sources.split(",") if s] if args.sources else list(ADAPTERS)

    log = {"run_date": today, "since": args.since, "dry_run": args.dry_run, "model": client.model if not args.dry_run else None,
           "sources": {}, "documents": [], "failures": [], "stopped_early": None}
    queue = []
    for name in sources:
        if name not in ADAPTERS:
            log["failures"].append({"source": name, "error": "unknown source"})
            continue
        list_fn, _ = ADAPTERS[name]
        try:
            items = list_fn(fetcher, args.since)
        except Exception as e:  # noqa: BLE001 - one broken source must not stop the others
            log["failures"].append({"source": name, "stage": "list", "error": f"{type(e).__name__}: {e}"[:300]})
            log["sources"][name] = {"listed": 0, "new": 0}
            continue
        new = [i for i in items if i["key"] not in state["seen"]
               and state["failed"].get(i["key"], {}).get("attempts", 0) < MAX_ATTEMPTS]
        log["sources"][name] = {"listed": len(items), "new": len(new)}
        queue += new

    # Newest first; undated items (LED news, dated only once opened) go last.
    queue.sort(key=lambda i: i.get("published") or "0000", reverse=True)
    processed = 0

    review_path = data_dir / "review" / "unknown-capex.json"
    review = load_json(review_path, [])
    totals = {"candidates": 0, "unknown_capex": 0, "below_threshold": 0, "dropped_fields": 0}

    def save_progress():
        # Saved after every document, so a crash or timeout never loses (or re-pays for) finished work.
        if not args.dry_run:
            write_json(state_path, state)
            write_json(review_path, review)

    for n, item in enumerate(queue):
        if processed >= args.max_docs or fetcher.requests >= args.max_requests:
            why = f"max {args.max_docs} documents" if processed >= args.max_docs else f"max {args.max_requests} web requests"
            log["stopped_early"] = f"{len(queue) - n} new documents left for later runs ({why} per run)"
            break
        entry = {"source": item["source"], "url": item["url"], "title": item.get("title"), "published": item.get("published")}
        log["documents"].append(entry)
        if args.dry_run:
            entry["result"] = "dry-run: listed only"
            continue
        try:
            if not loader_for(item)(fetcher, item, args.since):
                entry["result"] = "skipped: " + item.get("skip_reason", "older than backfill window")
                state["seen"][item["key"]] = {"first_seen": today, "result": "skipped"}
                save_progress()
                continue
            processed += 1
            res = extract(item, client, existing)
        except BudgetExceeded as e:
            log["stopped_early"] = str(e)
            entry["result"] = "not processed: budget reached"
            break
        except Exception as e:  # noqa: BLE001 - log, count the attempt, move on to the next document
            log["failures"].append({"source": item["source"], "url": item["url"], "stage": "load/extract",
                                    "error": f"{type(e).__name__}: {e}"[:300]})
            entry["result"] = "failed"
            f = state["failed"].setdefault(item["key"], {"attempts": 0})
            f["attempts"] += 1
            f["last_error"] = f"{type(e).__name__}: {e}"[:200]
            f["last_tried"] = today
            save_progress()
            continue

        slug = slug_for(item)
        snap = item["text"].encode("utf-8")[:SNAPSHOT_MAX_BYTES].decode("utf-8", "ignore")
        snap_path = data_dir / "snapshots" / f"{slug}.txt"
        snap_path.parent.mkdir(parents=True, exist_ok=True)
        snap_path.write_text(snap)
        source_draft = {
            "url": item["url"], "publisher": item["publisher"], "doc_type": item["doc_type"], "primary": item["primary"],
            "published": item.get("published"), "retrieved_at": today, "retrieved_by": "collector",
            "snapshot_path": snap_path.name, "terms_status": "approved", "title": item.get("title"),
        }
        if res["candidates"] or res["unknown_capex"]:
            write_json(data_dir / "candidates" / today / f"{slug}.json", {
                "source": source_draft, "candidates": res["candidates"], "model": client.model,
                "truncated": res["truncated"], "dropped": res["dropped"]})
        for u in res["unknown_capex"]:
            review.append({"found": today, "source_url": item["url"], "snapshot_path": snap_path.name, **u})
        totals["candidates"] += len(res["candidates"])
        totals["unknown_capex"] += len(res["unknown_capex"])
        totals["below_threshold"] += len(res["below_threshold"])
        totals["dropped_fields"] += len(res["dropped"])
        entry["result"] = f'{len(res["candidates"])} candidate(s), {len(res["unknown_capex"])} without value'
        state["seen"][item["key"]] = {"first_seen": today, "result": entry["result"], "snapshot": snap_path.name}
        state["failed"].pop(item["key"], None)
        save_progress()

    log["totals"] = totals
    log["requests"] = fetcher.requests
    log["claude"] = {"calls": client.calls, "input_tokens": client.input_tokens, "output_tokens": client.output_tokens,
                     "cost_usd": round(client.cost, 4)}
    save_progress()
    write_json(data_dir / "runs" / f"{today}.json", log)
    return log


def summary_markdown(log):
    t = log.get("totals", {})
    lines = [f"## Collector run {log['run_date']}" + (" (dry run)" if log["dry_run"] else ""), "",
             f"- Candidates (value of $10M or more, every field quote-checked): **{t.get('candidates', 0)}**",
             f"- Projects found without a stated value (in `data/review/unknown-capex.json`): {t.get('unknown_capex', 0)}",
             f"- Below the $10M threshold (ignored): {t.get('below_threshold', 0)}",
             f"- Fields dropped because their quote wasn't in the document: {t.get('dropped_fields', 0)}",
             f"- Claude: {log['claude']['calls']} calls, ${log['claude']['cost_usd']:.2f}",
             f"- Web requests: {log['requests']}", ""]
    lines.append("| Source | Listed | New |")
    lines.append("|---|---|---|")
    for name, s in log["sources"].items():
        lines.append(f"| {name} | {s['listed']} | {s['new']} |")
    if log.get("stopped_early"):
        lines += ["", f"Stopped early: {log['stopped_early']}"]
    if log["failures"]:
        lines += ["", "### Failures"] + [f"- {f.get('source')}: {f.get('error')}" for f in log["failures"][:20]]
    lines += ["", "Candidates are not published until they are reviewed and merged into `data/projects/` (M4)."]
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--since", default=os.environ.get("COLLECTOR_SINCE", DEFAULT_SINCE))
    ap.add_argument("--max-docs", type=int, default=int(os.environ.get("COLLECTOR_MAX_DOCS", "40")))
    ap.add_argument("--max-requests", type=int, default=int(os.environ.get("COLLECTOR_MAX_REQUESTS", "200")),
                    help="stop after this many web requests (about 35 minutes at LED's 10-second spacing)")
    ap.add_argument("--budget", type=float, default=float(os.environ.get("COLLECTOR_BUDGET_USD", "1.50")))
    ap.add_argument("--sources", default=os.environ.get("COLLECTOR_SOURCES", ""))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--summary", help="also write a markdown summary to this path")
    args = ap.parse_args(argv)
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", args.since):
        ap.error("--since must be YYYY-MM-DD")
    if not args.dry_run and not os.environ.get("ANTHROPIC_API_KEY"):
        ap.error("ANTHROPIC_API_KEY is not set (use --dry-run to list documents without Claude)")
    log = run(args)
    md = summary_markdown(log)
    if args.summary:
        pathlib.Path(args.summary).write_text(md)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
