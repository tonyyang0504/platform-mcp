# Jobicy MCP server

Category: **deals** · Docs: https://jobicy.com/jobs-rss-feed · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/deals/jobicy.json`; edit the catalog, not this file.

## Tools

- `search_postings` — `GET /remote-jobs` (https://jobicy.com/jobs-rss-feed)
- ~~`me`~~ not offered: No credentials to verify ('auth: none') and no account endpoint.
- ~~`get_posting`~~ not offered: No per-id endpoint is documented; the feed returns whole records.
- ~~`submit_bid`~~ not offered: Fair use: 'redirect applicants to the original job URL' — no application or bid API.
- ~~`withdraw_bid`~~ not offered: No bid API (see submit_bid).
- ~~`bid_status`~~ not offered: No bid API (see submit_bid).
- ~~`list_messages`~~ not offered: No messaging API; the page documents the public listing feed only.
- ~~`send_message`~~ not offered: No messaging API; the page documents the public listing feed only.
- ~~`credits`~~ not offered: No account or credit endpoint; the feed is keyless.

## Credentials

None.

## Run

    uvx platform-mcp-hub serve deals/jobicy          # Python
    npx -y platform-mcp-hub serve deals/jobicy       # TypeScript
    claude mcp add jobicy -- uvx platform-mcp-hub serve deals/jobicy

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/jobicy-deals-mcp`. Python and TypeScript serve identical tools.
