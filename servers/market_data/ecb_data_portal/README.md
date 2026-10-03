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

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve ecb_data_portal   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve ecb_data_portal
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve ecb_data_portal   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/ecb_data_portal-mcp`. Python and TypeScript serve identical tools.
