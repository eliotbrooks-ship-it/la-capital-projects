"""Source adapters for the sources marked `approved` in docs/sources.md.

Each adapter has two steps so the run cap applies before the expensive part:
  list_items(fetcher, since)  -> cheap listing of Item dicts (no document downloads)
  load(fetcher, item)         -> fills item["text"] (and maybe item["published"]); returns False to skip

Item keys: key (unique id for run state), source (adapter name), url, title, published (YYYY-MM-DD or None),
publisher, doc_type, primary, kind ("html" | "pdf" | "text").
"""
import json
import re
import urllib.parse
import xml.etree.ElementTree as ET

from .fetch import decode
from .text import html_to_text, pdf_to_text

LED_SITEMAP_INDEX = "https://admin.opportunitylouisiana.gov/sitemap_index.xml"
LED_BCI_PAGE = "https://www.opportunitylouisiana.gov/about-led/advisory-boards/louisiana-board-of-commerce-and-industry"
VPPJ_HOME = "https://vppj.org/index.html"
CIVICCLERK_API = "https://ascensionparishla.api.civicclerk.com/v1"
CAMERON_FEED = "https://cameronpj.org/category/police-jury-meetings/agendas/feed/"

# LED news slugs worth reading. Everything else (events, awards, seminars) is skipped without a download.
LED_SLUG_KEYWORDS = re.compile(
    r"invest|million|billion|facility|plant|expan|project|jobs|locat|headquarter|manufactur|construct|build|"
    r"lng|data-center|hydrogen|ammonia|steel|chemical|refin|terminal|mill|site|fid|campus|port|pipeline|solar|power",
    re.I)
SM_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def _item(**kw):
    base = {"published": None, "primary": True, "kind": "html", "title": ""}
    base.update(kw)
    return base


def _date_only(s):
    m = re.match(r"(\d{4}-\d{2}-\d{2})", s or "")
    return m.group(1) if m else None


# ---------------------------------------------------------------- LED news (sitemap)
def led_news_list(fetcher, since):
    data, _ = fetcher.get(LED_SITEMAP_INDEX)
    root = ET.fromstring(data)
    maps = [(loc.text or "").strip() for loc in root.findall("sm:sitemap/sm:loc", SM_NS)]
    maps = [m for m in maps if re.search(r"/post-sitemap\d*\.xml$", m)]
    items = []
    for sm_url in maps:
        sdata, _ = fetcher.get(sm_url)
        for u in ET.fromstring(sdata).findall("sm:url", SM_NS):
            loc = (u.findtext("sm:loc", "", SM_NS) or "").strip()
            lastmod = _date_only(u.findtext("sm:lastmod", "", SM_NS))
            if "/news/" not in loc:
                continue
            # lastmod is when the post was last edited, so it is never earlier than publication:
            # anything last edited before the backfill window can be skipped without a download.
            if lastmod and lastmod < since:
                continue
            slug = loc.rstrip("/").rsplit("/", 1)[-1]
            if not LED_SLUG_KEYWORDS.search(slug):
                continue
            # The admin host serves the CMS; readers use www. Same path on both.
            public = loc.replace("://admin.opportunitylouisiana.gov/", "://www.opportunitylouisiana.gov/")
            items.append(_item(key=public, source="led_news", url=public, title=slug.replace("-", " "),
                               published=lastmod, publisher="Louisiana Economic Development", doc_type="press_release"))
    return items


def led_news_load(fetcher, item, since):
    data, ctype = fetcher.get(item["url"])
    page = html_to_text(decode(data, ctype))
    pub = _date_only(page["meta"].get("article:published_time"))
    item["published"] = pub or item.get("published")  # fall back to the sitemap lastmod
    item["title"] = page["meta"].get("og:title") or page["title"] or item["title"]
    if pub and pub < since:
        return False  # older than the backfill window; remembered so it isn't fetched again
    item["text"] = page["text"]
    return True


# ---------------------------------------------------------------- LED Board of Commerce & Industry PDFs
def led_bci_list(fetcher, since):
    data, ctype = fetcher.get(LED_BCI_PAGE)
    page = html_to_text(decode(data, ctype))
    year0 = int(since[:4])
    items, seen = [], set()
    for href, label in page["links"]:
        url = urllib.parse.urljoin(LED_BCI_PAGE, href)
        m = re.search(r"/wp-content/uploads/(\d{4})/(\d{2})/[^/]+\.pdf$", url, re.I)
        if not m or int(m.group(1)) < year0 or url in seen:
            continue
        seen.add(url)
        is_itep = "ITE" in url.rsplit("/", 1)[-1] or "Application" in label
        items.append(_item(key=url, source="led_bci", url=url, title=label or url.rsplit("/", 1)[-1],
                           published=f"{m.group(1)}-{m.group(2)}-01", publisher="Louisiana Economic Development",
                           doc_type="itep_notice" if is_itep else "other", kind="pdf"))
    return items


# ---------------------------------------------------------------- Vermilion Parish Police Jury agendas
def vppj_list(fetcher, since):
    data, ctype = fetcher.get(VPPJ_HOME)
    page = html_to_text(decode(data, ctype))
    items, seen = [], set()
    for href, label in page["links"]:
        url = urllib.parse.urljoin(VPPJ_HOME, href)
        if "/PDFforms/Agendas/" not in url or not url.lower().endswith(".pdf"):
            continue
        url = urllib.parse.quote(url, safe=":/%")  # file names contain spaces
        if url in seen:
            continue
        seen.add(url)
        m = re.search(r"(\d{2})-(\d{2})-(\d{2})\.pdf$", urllib.parse.unquote(url))
        published = f"20{m.group(3)}-{m.group(1)}-{m.group(2)}" if m else None
        if published and published < since:
            continue
        items.append(_item(key=url, source="vppj", url=url, title=label or urllib.parse.unquote(url.rsplit("/", 1)[-1]),
                           published=published, publisher="Vermilion Parish Police Jury", doc_type="parish_agenda", kind="pdf"))
    return items


# ---------------------------------------------------------------- Ascension Parish Council (CivicClerk API)
def ascension_list(fetcher, since):
    query = urllib.parse.urlencode({"$filter": f"startDateTime ge {since}T00:00:00Z", "$orderby": "startDateTime desc", "$top": "200"},
                                   quote_via=urllib.parse.quote)
    data, ctype = fetcher.get(f"{CIVICCLERK_API}/Events?{query}")
    items = []
    payload = json.loads(decode(data, ctype))
    events = payload.get("value", []) if isinstance(payload, dict) else []
    for ev in events:
        if not isinstance(ev, dict):
            continue
        for f in ev.get("publishedFiles") or []:
            if f.get("type") != "Agenda":  # skip packets: very large, and the agenda lists the items
                continue
            fid = f.get("fileId")
            text_url = f"{CIVICCLERK_API}/Meetings/GetMeetingFileStream(fileId={fid},plainText=true)"
            pdf_url = f"{CIVICCLERK_API}/Meetings/GetMeetingFileStream(fileId={fid},plainText=false)"
            items.append(_item(key=f"civicclerk:ascension:{fid}", source="ascension", url=pdf_url, text_url=text_url,
                               title=f'{ev.get("eventName", "Meeting")}: {f.get("name", "Agenda")}',
                               published=_date_only(ev.get("startDateTime")), publisher="Ascension Parish Council",
                               doc_type="parish_agenda", kind="text"))
    return items


def ascension_load(fetcher, item, since):
    data, ctype = fetcher.get(item["text_url"])
    text = decode(data, ctype)
    if "html" in ctype.lower():
        text = html_to_text(text)["text"]
    item["text"] = text
    return True


# ---------------------------------------------------------------- Cameron Parish Police Jury (RSS)
def cameron_list(fetcher, since):
    data, _ = fetcher.get(CAMERON_FEED)
    root = ET.fromstring(data)
    content_tag = "{http://purl.org/rss/1.0/modules/content/}encoded"
    items = []
    for it in root.iter("item"):
        link = (it.findtext("link") or "").strip()
        title = (it.findtext("title") or "").strip()
        pub = it.findtext("pubDate") or ""
        try:
            from email.utils import parsedate_to_datetime
            published = parsedate_to_datetime(pub).date().isoformat()
        except (TypeError, ValueError):
            published = None
        if published and published < since:
            continue
        body = (it.findtext(content_tag) or "") + (it.findtext("description") or "")
        pdfs = re.findall(r'href="([^"]+\.pdf)"', body, re.I)
        pdf = urllib.parse.urljoin(link or CAMERON_FEED, pdfs[0]) if pdfs else None
        items.append(_item(key=pdf or link, source="cameron", url=pdf or link, page_url=link, title=title,
                           published=published, publisher="Cameron Parish Police Jury", doc_type="parish_agenda",
                           kind="pdf" if pdf else "html"))
    return items


# ---------------------------------------------------------------- shared loaders
def pdf_load(fetcher, item, since):
    data, _ = fetcher.get(item["url"])
    text = pdf_to_text(data)
    if len(text) < 200:
        item["skip_reason"] = "no text layer (scanned PDF?) or pdftotext unavailable"
        return False
    item["text"] = text
    return True


def html_load(fetcher, item, since):
    data, ctype = fetcher.get(item["url"])
    page = html_to_text(decode(data, ctype))
    item["text"] = page["text"]
    return True


ADAPTERS = {
    "led_news": (led_news_list, led_news_load),
    "led_bci": (led_bci_list, pdf_load),
    "vppj": (vppj_list, pdf_load),
    "ascension": (ascension_list, ascension_load),
    "cameron": (cameron_list, None),  # loader chosen by kind
}


def loader_for(item):
    _, load = ADAPTERS[item["source"]]
    if load:
        return load
    return pdf_load if item["kind"] == "pdf" else html_load
