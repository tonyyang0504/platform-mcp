# World Bank Indicators API MCP server

Category: **market_data** · Docs: https://datahelpdesk.worldbank.org/knowledgebase/articles/898581-api-basic-call-structures · Verified: 2026-10-01

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/market_data/world_bank_indicators.json`; edit the catalog, not this file.

## Tools

- `get_series` — `GET /country/{country}/indicator/{indicator}` (https://datahelpdesk.worldbank.org/knowledgebase/articles/898599-indicator-api-queries)
- ~~`me`~~ not offered: Open data: no accounts.
- ~~`get_candles`~~ not offered: No OHLC data.
- ~~`search_symbols`~~ not offered: The API lists indicators (/v2/indicator, ~29,000, paged) but has no search parameter; mapping `query` would fake a search.
- ~~`get_news`~~ not offered: No news endpoint.

## Credentials

None.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve world_bank_indicators   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve world_bank_indicators
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve world_bank_indicators   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/world_bank_indicators-mcp`. Python and TypeScript serve identical tools.
