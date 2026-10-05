"""Turn HTML and PDF documents into plain text, and normalise text for quote matching."""
import html
import re
import shutil
import subprocess
import tempfile
import unicodedata
from html.parser import HTMLParser

SKIP_TAGS = {"script", "style", "noscript", "nav", "header", "footer", "form", "svg", "iframe", "aside"}
BLOCK_TAGS = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "section", "article", "table", "ul", "ol"}


class _Extractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip = 0
        self.parts = []
        self.main_parts = None  # text inside <article> or <main>, if any
        self.main_depth = 0
        self.meta = {}
        self.links = []
        self.title = ""
        self._in_title = False
        self._in_a = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta":
            key = a.get("property") or a.get("name")
            if key and "content" in a:
                self.meta[key.lower()] = a["content"]
        if tag == "a" and a.get("href"):
            self.links.append((a["href"], ""))
            self._in_a = True
        if tag == "title":
            self._in_title = True
        if tag in SKIP_TAGS:
            self.skip += 1
        if tag in ("article", "main"):
            if self.main_parts is None:
                self.main_parts = []
            self.main_depth += 1
        if tag in BLOCK_TAGS:
            self._emit("\n")

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        if tag == "a":
            self._in_a = False
        if tag in SKIP_TAGS and self.skip:
            self.skip -= 1
        if tag in ("article", "main") and self.main_depth:
            self.main_depth -= 1
        if tag in BLOCK_TAGS:
            self._emit("\n")

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        if self._in_a and self.links and data.strip():
            href, label = self.links[-1]
            self.links[-1] = (href, (label + " " + data.strip()).strip())
        if not self.skip:
            self._emit(data)

    def _emit(self, s):
        self.parts.append(s)
        if self.main_depth and self.main_parts is not None:
            self.main_parts.append(s)


def _tidy(s):
    s = re.sub(r"[ \t\r\f\v]+", " ", s)
    s = re.sub(r" *\n *", "\n", s)
    return re.sub(r"\n{3,}", "\n\n", s).strip()


def html_to_text(raw):
    """Return dict(text, title, meta, links). Prefers <article>/<main> content when present."""
    p = _Extractor()
    p.feed(raw if isinstance(raw, str) else raw.decode("utf-8", "replace"))
    body = "".join(p.main_parts) if p.main_parts else "".join(p.parts)
    return {"text": _tidy(body), "title": _tidy(html.unescape(p.title)), "meta": p.meta, "links": p.links}


def pdf_to_text(data):
    """Extract text with the `pdftotext` command (poppler-utils). Returns '' if unavailable or no text layer."""
    exe = shutil.which("pdftotext")
    if not exe:
        return ""
    with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
        f.write(data)
        f.flush()
        try:
            out = subprocess.run([exe, "-enc", "UTF-8", f.name, "-"], capture_output=True, timeout=120)
        except subprocess.TimeoutExpired:
            return ""
    return _tidy(out.stdout.decode("utf-8", "replace")) if out.returncode == 0 else ""


QUOTE_CHARS = {"‘": "'", "’": "'", "‚": "'", "‛": "'", "′": "'",
               "“": '"', "”": '"', "„": '"', "″": '"',
               "–": "-", "—": "-", "‒": "-", "−": "-", " ": " ", " ": " ", " ": " "}


def normalise(s):
    """Lower-case, unify quotes/dashes/spaces and collapse whitespace so quotes can be matched reliably."""
    s = unicodedata.normalize("NFKC", s)
    s = "".join(QUOTE_CHARS.get(ch, ch) for ch in s)
    return re.sub(r"\s+", " ", s).strip().lower()


def quote_in(quote, normalised_doc):
    q = normalise(quote or "")
    return len(q) >= 15 and q in normalised_doc


_SCALE = {"thousand": 1e3, "k": 1e3, "million": 1e6, "mil": 1e6, "m": 1e6, "mm": 1e6, "billion": 1e9, "bn": 1e9, "b": 1e9, "trillion": 1e12}


def numbers_in(quote):
    """All numbers written in a quote, with scale words applied: '$1.2 billion' -> {1.2, 1200000000.0}."""
    found = set()
    for m in re.finditer(r"(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)\s*-?\s*(thousand|million|billion|trillion|mil|mm|bn|k|m|b)?\b",
                         normalise(quote or "")):
        n = float(m.group(1).replace(",", ""))
        found.add(n)
        if m.group(2):
            found.add(n * _SCALE[m.group(2)])
    return found


def number_supported(value, quote, tolerance=0.01):
    """True if `value` (int/float) is written in the quote, within 1%."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return any(abs(n - value) <= tolerance * max(abs(value), 1) for n in numbers_in(quote))
