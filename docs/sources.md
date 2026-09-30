# Source register

Checked 2026-09-30 with web search and page fetches. A collector may only be switched on for a source marked **approved**. This is a summary of what each site says, not legal advice. None of the policy pages read say anything explicit about automated access.

Confidence: HIGH = read directly; MEDIUM = inferred; LOW = guess.

| Source | URL | Access method | Terms / policy | robots.txt | Status | Rate limit | Confidence |
|---|---|---|---|---|---|---|---|
| LED news | https://www.opportunitylouisiana.gov/news | HTML listing with filters. No RSS (`/rss` returns 404). WordPress back end at `admin.opportunitylouisiana.gov` with a sitemap. | [Privacy policy](https://www.opportunitylouisiana.gov/privacy-policy) only. Nothing on reuse or automated access. Contact: ledpress@la.gov | `www` has none (404). The admin host sets `Crawl-delay: 10` and disallows `/wp-json/` and `/?rest_route=`. | approved | 1 request per 10 s; daily | HIGH |
| LED Board of Commerce & Industry (agendas, ITEP approvals) | https://www.opportunitylouisiana.gov/about-led/advisory-boards/louisiana-board-of-commerce-and-industry | Year-by-year page linking to PDFs under `admin.opportunitylouisiana.gov/wp-content/uploads/`. Latest is the 23 Sept 2026 agenda plus the ITEP approved-applications PDFs. | Same LED privacy policy | Admin host crawl-delay 10; uploads are not disallowed | approved | 1 request per 10 s; after each board meeting | HIGH |
| LPSC Document Access Center | https://lpscpubvalence.lpsc.louisiana.gov/portal/lpsc-web-portal | Search portal that needs JavaScript. Has PDF, Excel and **RSS** export. | [Disclaimer](https://lpsc.louisiana.gov/Disclaimer): not an official copy; accuracy not guaranteed; no liability for "improper or incorrect use of the data". Nothing on reuse or scraping. | `lpsc.louisiana.gov` has none (404). The portal host returns an HTML page with `noindex` instead of a robots file. | **ask** | 1 request per 15 s once approved; prefer the RSS export | HIGH (text), MEDIUM (status) |
| LDEQ EDMS | https://edms.deq.louisiana.gov/edmsv2 (info page https://deq.louisiana.gov/page/edms) | Search application | [Privacy page](https://www.deq.louisiana.gov/about-ldeq/privacy-page) reserves the right to act against anyone who "inappropriately use[s]" the site, and says systems are monitored | Our fetch tool refused the EDMS host as disallowed by robots.txt | **blocked** (automated). Manual lookups only. | none | HIGH (refusal), MEDIUM (actual rules) |
| Vermilion Parish Police Jury | https://vppj.org/ | Static pages linking to agenda PDFs (`/PDFforms/Agendas/Agendas 2026/`) | No policy links found | Empty file, so no rules | approved | 1 request per 20 s; weekly | HIGH / MEDIUM |
| Ascension Parish Council | https://ascensionparishla.portal.civicclerk.com/ | CivicClerk portal (needs JavaScript) | No policy links found | CivicClerk: `User-agent: *`, nothing disallowed | approved | 1 request per 15 s; weekly | HIGH / MEDIUM |
| Cameron Parish Police Jury | https://cameronpj.org/police-jury/agendas-minutes/ | WordPress, with **RSS** at `/category/police-jury-meetings/agendas/feed/` | No policy links found | Yoast default: nothing disallowed | approved | Use RSS; daily | HIGH |
| Calcasieu Parish Police Jury | https://www.calcasieu.gov/services/pj-minutes-and-agendas | Web pages; platform unclear (possibly Granicus) | Not found | 403 when fetched; the agenda archive also returned 403 | **ask** | 1 request per 30 s once approved | HIGH (403s), LOW (platform) |
| Plaquemines Parish Council | https://www.plaqueminesparish.gov/AgendaCenter | CivicPlus Agenda Center | Not found | Could not fetch | **ask** | 1 request per 20 s once approved | MEDIUM |
| St. James Parish Council | https://www.stjamesla.com/AgendaCenter/Parish-Council-3 | CivicPlus Agenda Center (from search results) | Could not fetch | Could not fetch | **ask** | 1 request per 20 s once approved | MEDIUM |
| Richland Parish Police Jury | No official website found. Facebook pages and newspaper public notices only. | Not applicable | Not applicable | Not applicable | **ask** (manual only) | none | MEDIUM |
| `rppjinfo.com` | Appears in searches for "Richland Parish Police Jury" | **Not the police jury.** It is a Canadian online-casino affiliate site. | Not applicable | Not applicable | **blocked** | none | HIGH |

## Hand-read sources (not collected automatically)

These are company press releases and news articles cited in the seed records. They were read by hand and are marked `terms_status: n/a`: Hyundai Motor Group, Woodside, Venture Global, Business Wire, Louisiana Illuminator, Fortune and Recycling Today. Automated collection from them would need its own terms check first.

## Still to do by hand

- Read the CivicPlus "Municipal Websites (CivicEngage) Terms", which may apply to the Plaquemines and St. James sites.
- Confirm the Calcasieu platform and robots.txt from a normal browser.
- Add more parishes as Tier B and C projects appear.
