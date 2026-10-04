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

    uvx platform-mcp-hub serve uk_find_a_tender          # Python
    npx -y platform-mcp-hub serve uk_find_a_tender       # TypeScript
    claude mcp add uk_find_a_tender -- uvx platform-mcp-hub serve uk_find_a_tender

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/uk_find_a_tender-mcp`. Python and TypeScript serve identical tools.
