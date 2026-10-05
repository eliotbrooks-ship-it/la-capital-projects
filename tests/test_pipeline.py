"""Offline tests for the collector. No network and no Claude calls: sources and the API are faked.

Run: python3 -m unittest discover -s tests -q
"""
import argparse
import io
import json
import pathlib
import shutil
import sys
import tempfile
import unittest
import urllib.error

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline import collect, extract, sources, text  # noqa: E402
from pipeline.fetch import Fetcher, FetchError  # noqa: E402

ARTICLE = """<html><head><title>LED news</title>
<meta property="article:published_time" content="2026-05-04T14:00:00+00:00">
<meta property="og:title" content="Acme Steel announces $1.2 billion mill in Ascension Parish"></head>
<body><nav>Home About</nav><article><h1>Acme Steel announces mill</h1>
<p>BATON ROUGE &ndash; Acme Steel Corp. announced today it will invest $1.2 billion to build a new mill in Ascension Parish.</p>
<p>The project will create 400 direct new jobs. Construction is expected to begin in 2027, with operations starting in 2029.</p>
<p>Bechtel was selected as the engineering, procurement and construction contractor.</p>
</article><footer>Contact</footer></body></html>"""

OLD_ARTICLE = ARTICLE.replace("2026-05-04", "2019-02-01")

SITEMAP_INDEX = """<?xml version="1.0"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<sitemap><loc>https://admin.opportunitylouisiana.gov/post-sitemap.xml</loc></sitemap>
<sitemap><loc>https://admin.opportunitylouisiana.gov/page-sitemap.xml</loc></sitemap></sitemapindex>"""

POST_SITEMAP = """<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>https://admin.opportunitylouisiana.gov/news/acme-steel-announces-1-2-billion-mill/</loc><lastmod>2026-05-04T14:00:00+00:00</lastmod></url>
<url><loc>https://admin.opportunitylouisiana.gov/news/old-plant-expansion-in-2019/</loc><lastmod>2026-07-17T13:00:00+00:00</lastmod></url>
<url><loc>https://admin.opportunitylouisiana.gov/news/registration-now-open-for-seminar/</loc><lastmod>2026-07-17T13:00:00+00:00</lastmod></url>
</urlset>"""

CIVICCLERK = json.dumps({"value": [{"id": 1928, "eventName": "Parish Council", "startDateTime": "2026-10-07T18:00:00Z",
                                    "publishedFiles": [{"fileId": 10152, "type": "Agenda", "name": "Agenda 7Oct2026"},
                                                       {"fileId": 10153, "type": "Agenda Packet", "name": "Packet"}]}]})

RSS = """<?xml version="1.0"?><rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/"><channel>
<item><title>September 29, 2026 Board of Review</title><link>https://cameronpj.org/sept-29/</link>
<pubDate>Mon, 28 Sep 2026 15:57:03 +0000</pubDate>
<content:encoded><![CDATA[<p><a href="https://cameronpj.org/wp-content/uploads/2026/09/agenda.pdf">Agenda</a></p>]]></content:encoded></item>
<item><title>Old meeting</title><link>https://cameronpj.org/old/</link><pubDate>Mon, 01 Jan 2024 10:00:00 +0000</pubDate></item>
</channel></rss>"""

VPPJ = """<html><body>
<a href="PDFforms/Agendas/Agendas 2026/02.Feb2026/PJ Agenda 02-18-26.pdf">Police Jury Agenda</a>
<a href="PDFforms/Agendas/Agendas 2024/01.Jan2024/PJ Agenda 01-10-24.pdf">Old Agenda</a>
<a href="PDFforms/minutes/2026/PJ Minutes 02-18-26 - SIGNED.pdf">Minutes</a></body></html>"""

BCI = """<html><body><main>
<a href="https://admin.opportunitylouisiana.gov/wp-content/uploads/2026/09/ITE-Board-Approved-New-Apps-2024-Emergency-Rules-For-Website-Sept.-23-2026.pdf">9.23.26 – Application Approvals</a>
<a href="https://admin.opportunitylouisiana.gov/wp-content/uploads/2026/09/CI-Agenda-PUBVer-SEPT-23-2026_reduced.pdf">09.23.26 – Agenda</a>
<a href="https://admin.opportunitylouisiana.gov/wp-content/uploads/2023/02/CI-Agenda-old.pdf">old</a>
</main></body></html>"""


def tiny_pdf(message):
    """Build a minimal one-page PDF containing `message` as text (valid xref offsets)."""
    stream = f"BT /F1 12 Tf 72 720 Td ({message}) Tj ET".encode()
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
            b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    out, offsets = io.BytesIO(), []
    out.write(b"%PDF-1.4\n")
    for i, o in enumerate(objs, 1):
        offsets.append(out.tell())
        out.write(b"%d 0 obj\n" % i + o + b"\nendobj\n")
    xref = out.tell()
    out.write(b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1))
    for off in offsets:
        out.write(b"%010d 00000 n \n" % off)
    out.write(b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref))
    return out.getvalue()


class FakeFetcher:
    def __init__(self, pages):
        self.pages = pages
        self.requests = 0
        self.urls = []

    def get(self, url):
        self.requests += 1
        self.urls.append(url)
        if url not in self.pages:
            raise FetchError(f"HTTP 404 for {url}")
        body, ctype = self.pages[url]
        return (body.encode() if isinstance(body, str) else body), ctype


class FakeClient:
    """Stands in for ClaudeClient. Returns canned tool output; can simulate the budget running out."""
    model = "fake-model"

    def __init__(self, projects, budget_calls=99):
        self.projects = projects
        self.calls = self.input_tokens = self.output_tokens = 0
        self.cost = 0.0
        self.budget_calls = budget_calls

    def call(self, user_text):
        if self.calls >= self.budget_calls:
            raise extract.BudgetExceeded("budget reached")
        self.calls += 1
        self.input_tokens += 1000
        self.output_tokens += 100
        self.cost += 0.0015
        return json.loads(json.dumps(self.projects))


GOOD_PROJECT = {
    "name": {"value": "Acme Steel mill", "quote": "Acme Steel Corp. announced today it will invest $1.2 billion to build a new mill"},
    "owner_company": {"value": "Acme Steel Corp.", "quote": "Acme Steel Corp. announced today"},
    "project_type": {"value": "steel_metals", "quote": "build a new mill in Ascension Parish"},
    "parish": {"value": "Ascension Parish", "quote": "a new mill in Ascension Parish"},
    "capex": {"value_usd": 1200000000, "basis": "capex", "quote": "invest $1.2 billion"},
    "jobs": [{"kind": "permanent_direct", "value": 400, "quote": "create 400 direct new jobs"},
             {"kind": "construction_peak", "value": 9000, "quote": "employ 9,000 workers at peak"}],  # not in text
    "expected_completion": {"value": "2029", "basis": "first_operations", "quote": "with operations starting in 2029"},
    "contractors": [{"name": "Bechtel", "role": "epc", "quote": "Bechtel was selected as the engineering, procurement and construction contractor"}],
    "site_acres": {"value": 500, "quote": "a 500-acre site"},  # not in text
}


class TextTests(unittest.TestCase):
    def test_html_prefers_article_and_reads_meta(self):
        page = text.html_to_text(ARTICLE)
        self.assertIn("invest $1.2 billion", page["text"])
        self.assertNotIn("Home About", page["text"])
        self.assertEqual(page["meta"]["article:published_time"][:10], "2026-05-04")

    def test_quote_matching_ignores_curly_quotes_and_spacing(self):
        doc = text.normalise("The “Blue Point” plant – world’s largest.")
        self.assertTrue(text.quote_in('the "Blue Point" plant - world\'s   largest', doc))
        self.assertFalse(text.quote_in("the Red Point plant", doc))
        self.assertFalse(text.quote_in("plant", doc))  # too short to prove anything

    @unittest.skipUnless(shutil.which("pdftotext"), "pdftotext not installed")
    def test_pdf_to_text(self):
        self.assertIn("ITEP application 20250123-ITE", text.pdf_to_text(tiny_pdf("ITEP application 20250123-ITE approved")))


class VerifyTests(unittest.TestCase):
    def setUp(self):
        self.doc = text.normalise(text.html_to_text(ARTICLE)["text"])

    def test_keeps_quoted_fields_and_drops_invented_ones(self):
        fields, dropped = extract.verify(json.loads(json.dumps(GOOD_PROJECT)), self.doc)
        self.assertEqual(fields["capex"]["value_usd"], 1200000000)
        self.assertEqual(fields["parish"]["value"], "Ascension")  # canonical parish name
        self.assertEqual([j["kind"] for j in fields["jobs"]], ["permanent_direct"])
        self.assertNotIn("site_acres", fields)
        self.assertEqual(len(dropped), 2)

    def test_rejects_non_louisiana_parish_and_bad_dates(self):
        raw = {"name": GOOD_PROJECT["name"],
               "parish": {"value": "Harris County", "quote": "a new mill in Ascension Parish"},
               "expected_completion": {"value": "sometime 2029", "basis": "first_operations", "quote": "with operations starting in 2029"}}
        fields, dropped = extract.verify(raw, self.doc)
        self.assertNotIn("parish", fields)
        self.assertNotIn("expected_completion", fields)
        self.assertEqual(len(dropped), 2)

    def test_match_hints(self):
        existing = [{"id": "acme-steel", "name": "Acme Steel Mill", "owner_company": "Acme Steel Corp"},
                    {"id": "other", "name": "Blue Point One", "owner_company": "CF Industries"}]
        hints = extract.match_hints(GOOD_PROJECT, existing)
        self.assertEqual(hints[0]["project_id"], "acme-steel")
        self.assertEqual(len(hints), 1)


    def test_value_must_be_stated_in_its_quote(self):
        raw = {"name": GOOD_PROJECT["name"],
               "capex": {"value_usd": 12000000000, "basis": "capex", "quote": "invest $1.2 billion"},
               "jobs": [{"kind": "permanent_direct", "value": 4000, "quote": "create 400 direct new jobs"}]}
        fields, dropped = extract.verify(raw, self.doc)
        self.assertNotIn("capex", fields)
        self.assertNotIn("jobs", fields)
        self.assertTrue(all("not stated" in d for d in dropped))

    def test_malformed_model_output_never_crashes(self):
        for raw in ["just a string", None, 42,
                    {"name": "Acme Steel mill"},
                    {"name": {"quote": "Acme Steel Corp. announced today"}},
                    {"name": GOOD_PROJECT["name"], "capex": {"value_usd": "1200000000", "basis": "capex", "quote": "invest $1.2 billion"}},
                    {"name": GOOD_PROJECT["name"], "parish": {"value": None, "quote": "a new mill in Ascension Parish"}},
                    {"name": GOOD_PROJECT["name"], "jobs": "lots", "permits": [None, {"number": 5}]},
                    {"name": GOOD_PROJECT["name"], "status": {"value": "booming", "quote": "Acme Steel Corp. announced today"}}]:
            fields, _ = extract.verify(raw, self.doc)
            self.assertNotIn("capex", fields)
            self.assertNotIn("status", fields)

    def test_extract_survives_bad_entries(self):
        client = FakeClient(["junk", {"name": "plain string"}, GOOD_PROJECT])
        item = {"text": text.html_to_text(ARTICLE)["text"], "publisher": "LED", "url": "u", "title": "t"}
        res = extract.extract(item, client, [])
        self.assertEqual(len(res["candidates"]), 1)


class AdapterTests(unittest.TestCase):
    def test_led_news_list_filters_slugs_and_uses_www(self):
        f = FakeFetcher({sources.LED_SITEMAP_INDEX: (SITEMAP_INDEX, "text/xml"),
                         "https://admin.opportunitylouisiana.gov/post-sitemap.xml": (POST_SITEMAP, "text/xml")})
        items = sources.led_news_list(f, "2025-01-01")
        urls = [i["url"] for i in items]
        self.assertIn("https://www.opportunitylouisiana.gov/news/acme-steel-announces-1-2-billion-mill/", urls)
        self.assertFalse(any("registration" in u for u in urls))
        self.assertNotIn("https://admin.opportunitylouisiana.gov/page-sitemap.xml", f.urls)

    def test_led_news_load_skips_posts_before_backfill(self):
        url = "https://www.opportunitylouisiana.gov/news/old-plant-expansion-in-2019/"
        f = FakeFetcher({url: (OLD_ARTICLE, "text/html")})
        item = {"url": url, "title": "x"}
        self.assertFalse(sources.led_news_load(f, item, "2025-01-01"))
        self.assertEqual(item["published"], "2019-02-01")

    def test_led_bci_list(self):
        items = sources.led_bci_list(FakeFetcher({sources.LED_BCI_PAGE: (BCI, "text/html")}), "2025-01-01")
        self.assertEqual(len(items), 2)
        self.assertEqual({i["doc_type"] for i in items}, {"itep_notice", "other"})

    def test_vppj_list_encodes_spaces_and_skips_old_and_minutes(self):
        items = sources.vppj_list(FakeFetcher({sources.VPPJ_HOME: (VPPJ, "text/html")}), "2025-01-01")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["published"], "2026-02-18")
        self.assertIn("PJ%20Agenda%2002-18-26.pdf", items[0]["url"])

    def test_ascension_list_takes_agendas_not_packets(self):
        f = FakeFetcher({})
        f.get = lambda url: (CIVICCLERK.encode(), "application/json")
        items = sources.ascension_list(f, "2025-01-01")
        self.assertEqual(len(items), 1)
        self.assertIn("fileId=10152,plainText=true", items[0]["text_url"])

    def test_cameron_list_reads_pdf_link_and_skips_old(self):
        items = sources.cameron_list(FakeFetcher({sources.CAMERON_FEED: (RSS, "application/rss+xml")}), "2025-01-01")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["kind"], "pdf")
        self.assertEqual(items[0]["published"], "2026-09-28")


class FetcherTests(unittest.TestCase):
    def _opener(self, robots_body=None, robots_status=200):
        class Resp(io.BytesIO):
            headers = {"Content-Type": "text/plain"}

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        def opener(req, timeout=None):
            if req.full_url.endswith("/robots.txt"):
                if robots_status != 200:
                    raise urllib.error.HTTPError(req.full_url, robots_status, "x", {}, None)
                return Resp(robots_body.encode())
            return Resp(b"ok")
        return opener

    def test_respects_robots_disallow(self):
        f = Fetcher(sleep=lambda s: None, opener=self._opener("User-agent: *\nDisallow: /private/\n"))
        self.assertEqual(f.get("https://vppj.org/public.pdf")[0], b"ok")
        with self.assertRaises(FetchError):
            f.get("https://vppj.org/private/x.pdf")

    def test_missing_robots_allows_and_forbidden_robots_blocks(self):
        self.assertEqual(Fetcher(sleep=lambda s: None, opener=self._opener(robots_status=404)).get("https://cameronpj.org/a")[0], b"ok")
        with self.assertRaises(FetchError):
            Fetcher(sleep=lambda s: None, opener=self._opener(robots_status=403)).get("https://cameronpj.org/a")

    def test_blocked_hosts_never_fetched(self):
        with self.assertRaises(FetchError):
            Fetcher(sleep=lambda s: None, opener=self._opener("")).get("https://edms.deq.louisiana.gov/edmsv2/")

    def test_redirects_are_rechecked_against_block_list(self):
        def opener(req, timeout=None):
            if req.full_url.endswith("/robots.txt"):
                raise urllib.error.HTTPError(req.full_url, 404, "x", {}, None)
            raise urllib.error.HTTPError(req.full_url, 302, "Found", {"Location": "https://edms.deq.louisiana.gov/x"}, None)
        with self.assertRaises(FetchError) as cm:
            Fetcher(sleep=lambda s: None, opener=opener).get("https://cameronpj.org/a")
        self.assertIn("block list", str(cm.exception))

    def test_rate_limit_waits_between_requests(self):
        waits, t = [], [0.0]
        f = Fetcher(sleep=lambda s: waits.append(s), clock=lambda: t[0], opener=self._opener(""))
        f.get("https://vppj.org/a")  # robots + page
        self.assertTrue(waits and abs(waits[0] - 20) < 1e-6)


class RunTests(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        (self.tmp / "projects").mkdir()
        (self.tmp / "projects" / "acme.json").write_text(json.dumps({"id": "acme-steel", "name": "Acme Steel Mill", "owner_company": "Acme Steel Corp"}))
        self.pages = {
            sources.LED_SITEMAP_INDEX: (SITEMAP_INDEX, "text/xml"),
            "https://admin.opportunitylouisiana.gov/post-sitemap.xml": (POST_SITEMAP, "text/xml"),
            "https://www.opportunitylouisiana.gov/news/acme-steel-announces-1-2-billion-mill/": (ARTICLE, "text/html"),
            "https://www.opportunitylouisiana.gov/news/old-plant-expansion-in-2019/": (OLD_ARTICLE, "text/html"),
        }

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def args(self, **kw):
        base = dict(since="2025-01-01", max_docs=40, max_requests=200, budget=1.5, sources="led_news", dry_run=False)
        base.update(kw)
        return argparse.Namespace(**base)

    def test_end_to_end_writes_candidates_review_state_and_log(self):
        no_value = {"name": GOOD_PROJECT["name"], "parish": GOOD_PROJECT["parish"]}
        client = FakeClient([GOOD_PROJECT, no_value])
        log = collect.run(self.args(), fetcher=FakeFetcher(self.pages), client=client, today="2026-10-04", data_dir=self.tmp)
        cand_files = list((self.tmp / "candidates" / "2026-10-04").glob("*.json"))
        self.assertEqual(len(cand_files), 1)
        cand = json.loads(cand_files[0].read_text())
        self.assertEqual(cand["candidates"][0]["match_hints"][0]["project_id"], "acme-steel")
        self.assertEqual(cand["source"]["retrieved_by"], "collector")
        snap = self.tmp / "snapshots" / cand["source"]["snapshot_path"]
        self.assertIn("invest $1.2 billion", snap.read_text())
        self.assertEqual(len(json.loads((self.tmp / "review" / "unknown-capex.json").read_text())), 1)
        state = json.loads((self.tmp / "runs" / "state.json").read_text())
        self.assertEqual(len(state["seen"]), 2)  # new article + the old one skipped by date
        self.assertEqual(log["totals"]["candidates"], 1)
        self.assertEqual(log["claude"]["calls"], 1)

        # Second run: nothing new, no Claude calls.
        client2 = FakeClient([GOOD_PROJECT])
        log2 = collect.run(self.args(), fetcher=FakeFetcher(self.pages), client=client2, today="2026-10-11", data_dir=self.tmp)
        self.assertEqual(client2.calls, 0)
        self.assertEqual(log2["sources"]["led_news"]["new"], 0)

    def test_budget_stop_is_logged_and_unprocessed_docs_stay_unseen(self):
        log = collect.run(self.args(), fetcher=FakeFetcher(self.pages), client=FakeClient([GOOD_PROJECT], budget_calls=0),
                          today="2026-10-04", data_dir=self.tmp)
        self.assertIn("budget", log["stopped_early"])
        state = json.loads((self.tmp / "runs" / "state.json").read_text())
        self.assertNotIn("https://www.opportunitylouisiana.gov/news/acme-steel-announces-1-2-billion-mill/", state["seen"])

    def test_failed_documents_are_retried_then_given_up(self):
        class Boom(FakeClient):
            def call(self, user_text):
                raise RuntimeError("Claude output hit max_tokens")
        for day in ("2026-10-04", "2026-10-11", "2026-10-18"):
            collect.run(self.args(), fetcher=FakeFetcher(self.pages), client=Boom([]), today=day, data_dir=self.tmp)
        state = json.loads((self.tmp / "runs" / "state.json").read_text())
        key = "https://www.opportunitylouisiana.gov/news/acme-steel-announces-1-2-billion-mill/"
        self.assertEqual(state["failed"][key]["attempts"], 3)
        log = collect.run(self.args(), fetcher=FakeFetcher(self.pages), client=Boom([]), today="2026-10-25", data_dir=self.tmp)
        self.assertEqual(log["sources"]["led_news"]["new"], 0)

    def test_dry_run_lists_without_claude_or_state(self):
        client = FakeClient([GOOD_PROJECT])
        log = collect.run(self.args(dry_run=True), fetcher=FakeFetcher(self.pages), client=client, today="2026-10-04", data_dir=self.tmp)
        self.assertEqual(client.calls, 0)
        self.assertEqual(len(log["documents"]), 2)
        self.assertFalse((self.tmp / "runs" / "state.json").exists())

    def test_source_listing_failure_is_logged_not_fatal(self):
        log = collect.run(self.args(sources="led_news,cameron"), fetcher=FakeFetcher(self.pages), client=FakeClient([]),
                          today="2026-10-04", data_dir=self.tmp)
        self.assertTrue(any(f["source"] == "cameron" for f in log["failures"]))
        self.assertIn("led_news", log["sources"])


class ClientTests(unittest.TestCase):
    def test_request_shape_cost_and_tool_parsing(self):
        captured = {}

        class Resp(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        def opener(req, timeout=None):
            captured["headers"] = dict(req.header_items())
            captured["body"] = json.loads(req.data)
            out = {"content": [{"type": "tool_use", "name": "record_projects", "input": {"projects": [{"name": {"value": "X", "quote": "q"}}]}}],
                   "usage": {"input_tokens": 10000, "output_tokens": 1000}}
            return Resp(json.dumps(out).encode())

        c = extract.ClaudeClient(api_key="test-key", model="claude-haiku-4-5-20251001", opener=opener)
        projects = c.call("doc")
        self.assertEqual(projects[0]["name"]["value"], "X")
        self.assertEqual(captured["body"]["tool_choice"], {"type": "tool", "name": "record_projects"})
        self.assertEqual(captured["headers"]["Anthropic-version"], "2023-06-01")
        self.assertAlmostEqual(c.cost, 10000 / 1e6 * 1 + 1000 / 1e6 * 5)

    def test_truncated_output_raises(self):
        class Resp(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False
        out = {"stop_reason": "max_tokens", "content": [], "usage": {"input_tokens": 1, "output_tokens": 1}}
        c = extract.ClaudeClient(api_key="k", opener=lambda req, timeout=None: Resp(json.dumps(out).encode()))
        with self.assertRaises(RuntimeError):
            c.call("doc")

    def test_budget_enforced_before_call(self):
        c = extract.ClaudeClient(api_key="k", budget_usd=0.0, opener=lambda *a, **k: None)
        with self.assertRaises(extract.BudgetExceeded):
            c.call("doc")


if __name__ == "__main__":
    unittest.main()
