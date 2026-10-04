# Arbeitnow MCP server

Category: **deals** · Docs: https://www.arbeitnow.com/api/job-board-api · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/deals/arbeitnow.json`; edit the catalog, not this file.

## Tools

- `search_postings` — `GET /job-board-api` (https://www.arbeitnow.com/api/job-board-api)
- ~~`me`~~ not offered: No credentials to verify ('auth: none') and no account endpoint.
- ~~`get_posting`~~ not offered: No per-id endpoint is documented; the feed returns whole records.
- ~~`submit_bid`~~ not offered: Page: 'No bid / message / contract surface — Arbeitnow is a board; the employer's page takes the application.'
- ~~`withdraw_bid`~~ not offered: No bid API (see submit_bid).
- ~~`bid_status`~~ not offered: No bid API (see submit_bid).
- ~~`list_messages`~~ not offered: No messaging API; the page documents the public listing feed only.
- ~~`send_message`~~ not offered: No messaging API; the page documents the public listing feed only.
- ~~`credits`~~ not offered: No account or credit endpoint; the feed is keyless.

## Credentials

None.

## Run

    uvx platform-mcp-hub serve deals/arbeitnow          # Python
    npx -y platform-mcp-hub serve deals/arbeitnow       # TypeScript
    claude mcp add arbeitnow -- uvx platform-mcp-hub serve deals/arbeitnow

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/arbeitnow-deals-mcp`. Python and TypeScript serve identical tools.
