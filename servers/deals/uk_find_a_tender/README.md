# Find a Tender MCP server

Category: **deals** · Docs: https://www.find-tender.service.gov.uk/Developer/Documentation · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/deals/uk_find_a_tender.json`; edit the catalog, not this file.

## Tools

- `search_postings` — `GET /api/1.0/ocdsReleasePackages` (https://www.find-tender.service.gov.uk/apidocumentation/1.0/GET-ocdsReleasePackages)
- `get_posting` — `GET /api/1.0/ocdsRecordPackages/{id}` (https://www.find-tender.service.gov.uk/apidocumentation/1.0/GET-ocdsRecordPackages)
- ~~`submit_bid`~~ not offered: Page: 'bids on buyer portals' — Find a Tender is the notice board; there is no bid, message or account API.
- ~~`withdraw_bid`~~ not offered: No bid API (see submit_bid).
- ~~`bid_status`~~ not offered: No bid API (see submit_bid).
- ~~`list_messages`~~ not offered: No messaging API; the page documents the public listing feed only.
- ~~`send_message`~~ not offered: No messaging API; the page documents the public listing feed only.
- ~~`credits`~~ not offered: No account or credit endpoint; the feed is keyless.
- ~~`me`~~ not offered: No credentials to verify ('auth: none') and no account endpoint.

## Credentials

None.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve uk_find_a_tender   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve uk_find_a_tender
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve uk_find_a_tender   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/uk_find_a_tender-mcp`. Python and TypeScript serve identical tools.
