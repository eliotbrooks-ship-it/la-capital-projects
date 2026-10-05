# Collector (M3)

The collector looks for new documents on the approved sources, asks Claude to pull out capital-project facts, and keeps only the facts whose supporting quote really appears in the document. It never edits `data/projects/`. Results arrive in a single rolling pull request named "Collector results". If last week's pull request is still open, the next run adds to it rather than starting again, so no document is read or paid for twice. Merging them into project records is the Checker's job (M4) or yours by hand.

## What it reads

| Source | How | Rate limit |
|---|---|---|
| LED news | Sitemap (`admin.opportunitylouisiana.gov/post-sitemap*.xml`), then each article on www. Only article slugs that look like projects (invest, million, plant, jobs…) are opened. | 1 request / 10 s |
| LED Board of Commerce & Industry | PDF links on the board page: agendas, minutes, ITEP approval lists | 1 request / 10 s |
| Vermilion Parish Police Jury | Agenda PDFs linked from the home page | 1 request / 20 s |
| Ascension Parish Council | CivicClerk public API; agenda text only, not full packets | 1 request / 15 s |
| Cameron Parish Police Jury | Agendas RSS feed, then the linked PDF | 1 request / 15 s |

Every host's robots.txt is checked first. LDEQ EDMS and rppjinfo.com are hard-blocked in `pipeline/fetch.py`. Sources marked "ask" in `docs/sources.md` are not included.

## What it writes

| Path | What |
|---|---|
| `data/candidates/<date>/<doc>.json` | Candidate projects worth $10M or more, every field with its quote, plus "looks like existing project X" hints |
| `data/snapshots/<doc>.txt` | The exact text Claude saw (quotes are checked against it) |
| `data/review/unknown-capex.json` | Projects found without a stated value |
| `data/runs/<date>.json` | Run log: documents, failures, web requests, Claude calls, tokens, cost |
| `data/runs/state.json` | Documents already handled, so they aren't read or paid for twice |

## Limits per run

- At most 10 documents go to Claude by default (you can raise it to 40 when starting a run).
- At most 200 web requests (about 35 minutes at LED's spacing).
- The run stops when Claude spending reaches **$1.50**, so each run you start costs at most $1.50.
- Long documents are split into parts, and at most 4 parts (about 200,000 characters) are read.
- Anything left over is picked up by the next run.

## One-time setup (you, on GitHub)

1. **Create an API key** in the Anthropic Console, with an expiry (for example 90 days) and a monthly spend limit (for example $25). Never paste the key into chat, email or a file. When it expires, create a new one and replace the secret.
2. **Save it as a repo secret.** In the repo, go to Settings → Secrets and variables → Actions → **New repository secret**. Name it `ANTHROPIC_API_KEY` and paste the key there.
3. **Let the workflow open pull requests.** Go to Settings → Actions → General → Workflow permissions, choose **Read and write permissions**, tick **Allow GitHub Actions to create and approve pull requests**, and save.

## Running it

- **First, a dry run (free).** Go to Actions → **Collect** → Run workflow, and leave "List new documents only" ticked. The run summary shows what each source listed. Nothing is sent to Claude and no pull request is opened.
- **Then a small live run.** Untick dry run and set max documents to 5. The results arrive as a pull request named "Collector results (review before merging)", with counts and cost in its description. Later runs add a comment to that pull request until it's merged.
- **After that, whenever you want fresh data.** It never runs on its own. Each run picks up where the last one stopped.

If the API key secret is missing, a live run fails with a clear message, and GitHub emails you when a run fails.

## How a fact is accepted

1. Claude (Haiku 4.5) must give an exact quote for every field.
2. The quote must appear in the part of the document Claude was shown. Curly quotes, dashes and spacing don't matter.
3. The value must be written in its own quote:
   - Numbers (value, jobs, acreage, capacity) must match within 1%. "$1.2 billion" supports 1,200,000,000.
   - Permit and ITEP numbers must appear exactly.
   - Names must share a word with the quote.
   - Dates must include the year.
4. The parish must be one of Louisiana's 64 parishes.
5. Anything failing a check is dropped and listed under "dropped" in the candidate file.
6. If Claude's answer is cut off, or a document fails, it is retried on up to 3 runs and then left alone (see `failed` in `data/runs/state.json`).

## Tests

`python3 -m unittest discover -s tests -q` runs offline, with the web and Claude faked. The workflow runs the tests before every collection.
