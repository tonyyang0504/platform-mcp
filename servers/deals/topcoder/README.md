# Topcoder MCP server

Category: **deals** · Docs: https://api.topcoder.com/v6/challenges · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/deals/topcoder.json`; edit the catalog, not this file.

## Tools

- `search_postings` — `GET /v6/challenges` (https://api.topcoder.com/v6/challenges)
- `get_posting` — `GET /v6/challenges/{id}` (https://api.topcoder.com/v6/challenges)
- ~~`submit_bid`~~ not offered: Page: 'Registration / submission are UI actions until member APIs are documented' (member endpoints need a Topcoder JWT; docs unreachable).
- ~~`withdraw_bid`~~ not offered: No bid API (see submit_bid).
- ~~`bid_status`~~ not offered: No bid API (see submit_bid).
- ~~`list_messages`~~ not offered: No messaging API; the page documents the public listing feed only.
- ~~`send_message`~~ not offered: No messaging API; the page documents the public listing feed only.
- ~~`credits`~~ not offered: No account or credit endpoint; the feed is keyless.
- ~~`me`~~ not offered: No credentials to verify ('auth: none') and no account endpoint.

## Credentials

None.

## Run

    uvx platform-mcp-hub serve deals/topcoder          # Python
    npx -y platform-mcp-hub serve deals/topcoder       # TypeScript
    claude mcp add topcoder -- uvx platform-mcp-hub serve deals/topcoder

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/topcoder-deals-mcp`. Python and TypeScript serve identical tools.
