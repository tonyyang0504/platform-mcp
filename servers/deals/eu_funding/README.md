# EU Funding & Tenders Portal MCP server

Category: **deals** · Docs: https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/apis · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/deals/eu_funding.json`; edit the catalog, not this file.

## Tools

- `me` — `POST /search?apiKey=SEDIA&text=***` (https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/apis)
- `search_postings` — `POST /search?apiKey=SEDIA` (https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/apis)
- `get_posting` — `POST /search?apiKey=SEDIA` (https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/apis)
- ~~`submit_bid`~~ not offered: The portal APIs are read-only search services ('retrieve the full list of Call of Proposals - Topics / Call for Tenders', https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/apis); proposals and tenders are submitted in the Funding & Tenders Portal with EU Login.
- ~~`withdraw_bid`~~ not offered: No submission API exists (https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/apis lists only search services); withdrawals happen in the portal's submission system.
- ~~`bid_status`~~ not offered: Submission status is only visible in the logged-in portal (My Proposals); the public APIs listed at https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/apis are search services only.
- ~~`list_messages`~~ not offered: No messaging API: the public services are Grants & Tenders, Topic Details, Grant Updates, FAQ, Organisation Public Data, Partner Search and Projects & Results searches (https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/apis).
- ~~`send_message`~~ not offered: No messaging API: the public services are search services only (https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/apis).
- ~~`credits`~~ not offered: The portal has no credits or paid quota; the search API is public with apiKey=SEDIA (https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/support/apis).

## Credentials

None.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve eu_funding   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve eu_funding
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve eu_funding   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/eu_funding-mcp`. Python and TypeScript serve identical tools.
