"""Polite HTTP fetching: descriptive User-Agent, robots.txt checks and per-host rate limits.

Rate limits come from docs/sources.md. A host whose robots.txt can't be read with a 401/403 is
treated as disallowed (urllib.robotparser's behaviour); a missing robots.txt (404) allows everything.
"""
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser

USER_AGENT = "la-capital-projects-collector/0.1 (+https://github.com/eliotbrooks-ship-it/la-capital-projects)"
MAX_BYTES = 15 * 1024 * 1024  # never download more than 15 MB for one document

# Minimum seconds between requests to the same host (docs/sources.md).
HOST_DELAY = {
    "www.opportunitylouisiana.gov": 10,
    "opportunitylouisiana.gov": 10,
    "admin.opportunitylouisiana.gov": 10,
    "vppj.org": 20,
    "ascensionparishla.api.civicclerk.com": 15,
    "cameronpj.org": 15,
}
DEFAULT_DELAY = 20

# Hosts the collector must never touch (docs/sources.md "blocked").
BLOCKED_HOSTS = {"edms.deq.louisiana.gov", "rppjinfo.com"}


def is_blocked(host):
    host = (host or "").lower()
    return any(host == b or host.endswith("." + b) for b in BLOCKED_HOSTS)


class FetchError(Exception):
    pass


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Redirects are surfaced to Fetcher so the target gets the same robots/block-list/rate-limit checks."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_DEFAULT_OPENER = urllib.request.build_opener(_NoRedirect()).open


class Fetcher:
    """Fetches URLs while honouring robots.txt and per-host delays. Counts requests for the run log."""

    def __init__(self, sleep=time.sleep, clock=time.monotonic, opener=None):
        self._sleep = sleep
        self._clock = clock
        self._open = opener or _DEFAULT_OPENER
        self._last = {}
        self._robots = {}
        self._robots_note = {}
        self.requests = 0

    def _wait(self, host):
        delay = HOST_DELAY.get(host, DEFAULT_DELAY)
        last = self._last.get(host)
        if last is not None:
            remaining = delay - (self._clock() - last)
            if remaining > 0:
                self._sleep(remaining)
        self._last[host] = self._clock()

    def _raw_get(self, url, check=False, hops=0):
        if check and not self.allowed(url):
            host = urllib.parse.urlsplit(url).hostname or ""
            why = "on the block list" if is_blocked(host) else self._robots_note.get(host, "disallowed by robots.txt")
            raise FetchError(f"{why}: {url}")
        host = urllib.parse.urlsplit(url).hostname or ""
        self._wait(host)
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
        self.requests += 1
        try:
            with self._open(req, timeout=60) as resp:
                data = resp.read(MAX_BYTES + 1)
                ctype = resp.headers.get("Content-Type", "")
        except urllib.error.HTTPError as e:
            location = e.headers.get("Location") if e.headers else None
            if e.code in (301, 302, 303, 307, 308) and location and hops < 5:
                return self._raw_get(urllib.parse.urljoin(url, location), check=check, hops=hops + 1)
            raise FetchError(f"HTTP {e.code} for {url}") from e
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise FetchError(f"network error for {url}: {e}") from e
        if len(data) > MAX_BYTES:
            raise FetchError(f"larger than {MAX_BYTES} bytes: {url}")
        return data, ctype

    def allowed(self, url):
        parts = urllib.parse.urlsplit(url)
        host = parts.hostname or ""
        if is_blocked(host):
            return False
        if host not in self._robots:
            rp = urllib.robotparser.RobotFileParser()
            robots_url = f"{parts.scheme}://{parts.netloc}/robots.txt"
            try:
                data, _ = self._raw_get(robots_url)
                rp.parse(data.decode("utf-8", "replace").splitlines())
            except FetchError as e:
                msg = str(e)
                if "HTTP 401" in msg or "HTTP 403" in msg or "HTTP 429" in msg:
                    rp.disallow_all = True
                    self._robots_note[host] = f"robots.txt refused ({msg.split(' for ')[0]})"
                elif "HTTP 4" in msg:
                    rp.allow_all = True
                else:
                    rp.disallow_all = True  # network trouble: be conservative this run
                    self._robots_note[host] = "site unreachable (robots.txt could not be fetched)"
            self._robots[host] = rp
        return self._robots[host].can_fetch(USER_AGENT, url)

    def get(self, url):
        """Return (bytes, content_type). Raises FetchError, including when robots.txt disallows the URL."""
        return self._raw_get(url, check=True)


def decode(data, content_type=""):
    """Decode using the HTTP charset if given; else UTF-8, falling back to Windows-1252 (common on small sites)."""
    m = re.search(r"charset=([\w-]+)", content_type or "", re.I)
    if m:
        try:
            return data.decode(m.group(1), "replace")
        except LookupError:
            pass
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("cp1252", "replace")
