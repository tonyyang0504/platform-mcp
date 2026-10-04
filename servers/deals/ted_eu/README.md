# TED — Tenders Electronic Daily MCP server

Category: **deals** · Docs: https://api.ted.europa.eu/ · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/deals/ted_eu.json`; edit the catalog, not this file.

## Tools

- `search_postings` — `POST /v3/notices/search` (https://api.ted.europa.eu/api-v3.yaml)
- ~~`me`~~ not offered: No credentials to verify (the Search API needs no key) and no account endpoint.
- ~~`get_posting`~~ not offered: api-v3.yaml documents no GET by publication number: GET /v3/notices lists the caller's OWN submitted notices (API key), so the reference page's 'GET /v3/notices/{publication-number}' is UNCONFIRMED. Re-read a notice from the search hit (`url`/raw.links) or search with query publication-number=<id>.
- ~~`submit_bid`~~ not offered: Page: 'No submission API — tenders are lodged on the buyer's platform'; the only writes (/v3/notices/submit) publish notices for buyers with an EU Login API key.
- ~~`withdraw_bid`~~ not offered: No bid API (see submit_bid).
- ~~`bid_status`~~ not offered: No bid API (see submit_bid).
- ~~`list_messages`~~ not offered: No messaging API; the public API is notice search, render, convert and validate.
- ~~`send_message`~~ not offered: No messaging API; the public API is notice search, render, convert and validate.
- ~~`credits`~~ not offered: No account or credit endpoint; the Search API is keyless.

## Credentials

None.

## Run

    uvx platform-mcp-hub serve ted_eu          # Python
    npx -y platform-mcp-hub serve ted_eu       # TypeScript
    claude mcp add ted_eu -- uvx platform-mcp-hub serve ted_eu

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/ted_eu-mcp`. Python and TypeScript serve identical tools.
