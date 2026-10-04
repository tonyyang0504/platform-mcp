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

    uvx platform-mcp-hub serve world_bank_indicators          # Python
    npx -y platform-mcp-hub serve world_bank_indicators       # TypeScript
    claude mcp add world_bank_indicators -- uvx platform-mcp-hub serve world_bank_indicators

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/world_bank_indicators-mcp`. Python and TypeScript serve identical tools.
