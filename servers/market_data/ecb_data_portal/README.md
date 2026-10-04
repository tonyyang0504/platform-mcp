# ECB Data Portal (SDMX time series) MCP server

Category: **market_data** · Docs: https://data.ecb.europa.eu/help/api/data · Verified: 2026-09-27

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/market_data/ecb_data_portal.json`; edit the catalog, not this file.

## Tools

- `get_series` — `GET /data/{series_id}` (https://data.ecb.europa.eu/help/api/data)
- ~~`me`~~ not offered: Public statistical API without accounts or keys.
- ~~`get_candles`~~ not offered: Statistical time series only; no OHLC market candles.
- ~~`search_symbols`~~ not offered: The API lists dataflows (GET /service/dataflow) but offers no search over series keys.
- ~~`get_news`~~ not offered: No news in the statistical data API.

## Credentials

None.

## Run

    uvx platform-mcp-hub serve ecb_data_portal          # Python
    npx -y platform-mcp-hub serve ecb_data_portal       # TypeScript
    claude mcp add ecb_data_portal -- uvx platform-mcp-hub serve ecb_data_portal

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/ecb_data_portal-mcp`. Python and TypeScript serve identical tools.
