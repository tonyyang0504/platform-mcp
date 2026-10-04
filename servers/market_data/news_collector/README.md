# News RSS/GDELT/Fear&Greed MCP server

Category: **market_data** · Docs: https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/market_data/news_collector.json`; edit the catalog, not this file.

## Tools

- `get_news` — `GET /api/v2/doc/doc` (https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/)
- ~~`me`~~ not offered: No account: GDELT is keyless.
- ~~`get_candles`~~ not offered: News source; GDELT has no price data.
- ~~`get_series`~~ not offered: alternative.me Fear & Greed (https://alternative.me/crypto/fear-and-greed-index/#api) answers value as a JSON string ('71'), which the numeric `value` field cannot carry without a numeric-coercion expression in result mapping; GDELT timelines are a different mode not mapped here.
- ~~`search_symbols`~~ not offered: News source; no instrument search.

## Credentials

None.

## Run

    uvx platform-mcp-hub serve news_collector          # Python
    npx -y platform-mcp-hub serve news_collector       # TypeScript
    claude mcp add news_collector -- uvx platform-mcp-hub serve news_collector

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/news_collector-mcp`. Python and TypeScript serve identical tools.
