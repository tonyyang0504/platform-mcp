# FRED macro series (CSV) MCP server

Category: **market_data** · Docs: https://fred.stlouisfed.org/docs/api/fred/ · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/market_data/macro_collector.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /fred/series` (https://fred.stlouisfed.org/docs/api/fred/series.html)
- `get_series` — `GET /fred/series/observations` (https://fred.stlouisfed.org/docs/api/fred/series_observations.html)
- `search_symbols` — `GET /fred/series/search` (https://fred.stlouisfed.org/docs/api/fred/series_search.html)
- ~~`get_candles`~~ not offered: FRED serves observations (one value per date), not OHLC candles — use get_series.
- ~~`get_news`~~ not offered: No news endpoint on this API.

## Credentials

- `PLATFORM_MCP_MACRO_COLLECTOR_API_KEY` — FRED API key ('32 character alpha-numeric lowercase string') requested at https://fredaccount.stlouisfed.org/apikeys; sent as the api_key query parameter (https://fred.stlouisfed.org/docs/api/api_key.html). Terms: show 'This product uses the FRED® API but is not endorsed or certified by the Federal Reserve Bank of St. Louis.'

## Run

    uvx platform-mcp-hub serve macro_collector          # Python
    npx -y platform-mcp-hub serve macro_collector       # TypeScript
    claude mcp add macro_collector -- uvx platform-mcp-hub serve macro_collector

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/macro_collector-mcp`. Python and TypeScript serve identical tools.
