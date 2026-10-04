# Prozorro (Ukrainian public procurement) MCP server

Category: **deals** · Docs: https://prozorro-api-docs.readthedocs.io/uk/master/ · Verified: 2026-10-01

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/deals/prozorro.json`; edit the catalog, not this file.

## Tools

- `search_postings` — `GET /tenders` (https://prozorro-api-docs.readthedocs.io/uk/master/tendering/basic-actions/tender-listing.html)
- `get_posting` — `GET /tenders/{id}` (https://prozorro-api-docs.readthedocs.io/uk/master/tendering/basic-actions/tender-listing.html)
- ~~`me`~~ not offered: Bidding needs an accredited e-procurement platform (broker); the public API has no accounts.
- ~~`submit_bid`~~ not offered: Bids are placed through accredited brokers, not the public API.
- ~~`withdraw_bid`~~ not offered: Through accredited brokers only.
- ~~`bid_status`~~ not offered: Through accredited brokers only.
- ~~`list_messages`~~ not offered: Questions and answers are inside each tender record; no message inbox.
- ~~`send_message`~~ not offered: Through accredited brokers only.
- ~~`credits`~~ not offered: No credits.

## Credentials

None.

## Run

    uvx platform-mcp-hub serve prozorro          # Python
    npx -y platform-mcp-hub serve prozorro       # TypeScript
    claude mcp add prozorro -- uvx platform-mcp-hub serve prozorro

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/prozorro-mcp`. Python and TypeScript serve identical tools.
