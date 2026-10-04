# FL MCP server

Category: **deals** · Docs: https://www.fl.ru/rss/all.xml · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/deals/fl_ru.json`; edit the catalog, not this file.

## Tools

- `search_postings` — `GET /rss/all.xml` (https://www.fl.ru/rss/all.xml)
- ~~`me`~~ not offered: No credentials to verify ('auth: none'): the feed is public and has no account endpoint.
- ~~`get_posting`~~ not offered: The feed has no per-item endpoint; each posting's page (url) is HTML only. search_postings returns the whole record.
- ~~`submit_bid`~~ not offered: Bids ('ответы') are placed on fl.ru with a logged-in account (PRO for most projects); FL.ru publishes no developer API.
- ~~`withdraw_bid`~~ not offered: No bid API (see submit_bid).
- ~~`bid_status`~~ not offered: No bid API (see submit_bid).
- ~~`list_messages`~~ not offered: No messaging API; only the public feed is machine-readable.
- ~~`send_message`~~ not offered: No messaging API; only the public feed is machine-readable.
- ~~`credits`~~ not offered: No account or credit endpoint; the feed is keyless.

## Credentials

None.

## Run

    uvx platform-mcp-hub serve fl_ru          # Python
    npx -y platform-mcp-hub serve fl_ru       # TypeScript
    claude mcp add fl_ru -- uvx platform-mcp-hub serve fl_ru

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/fl_ru-mcp`. Python and TypeScript serve identical tools.
