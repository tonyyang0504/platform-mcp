# Work With Indies MCP server

Category: **deals** · Docs: https://workwithindies.com/careers/rss.xml · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/deals/work_with_indies.json`; edit the catalog, not this file.

## Tools

- `search_postings` — `GET /careers/rss.xml` (https://www.workwithindies.com/careers/rss.xml)
- ~~`me`~~ not offered: No credentials to verify ('auth: none'): the feed is public and has no account endpoint.
- ~~`get_posting`~~ not offered: The feed has no per-item endpoint; each posting's page (url) is HTML only. search_postings returns the whole record.
- ~~`submit_bid`~~ not offered: Applications go through each studio's own link; Work With Indies publishes no API.
- ~~`withdraw_bid`~~ not offered: No bid API (see submit_bid).
- ~~`bid_status`~~ not offered: No bid API (see submit_bid).
- ~~`list_messages`~~ not offered: No messaging API; only the public feed is machine-readable.
- ~~`send_message`~~ not offered: No messaging API; only the public feed is machine-readable.
- ~~`credits`~~ not offered: No account or credit endpoint; the feed is keyless.

## Credentials

None.

## Run

    uvx platform-mcp-hub serve deals/work_with_indies          # Python
    npx -y platform-mcp-hub serve deals/work_with_indies       # TypeScript
    claude mcp add work_with_indies -- uvx platform-mcp-hub serve deals/work_with_indies

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/work_with_indies-deals-mcp`. Python and TypeScript serve identical tools.
