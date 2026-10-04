# Binance (ccxt) candles MCP server

Category: **market_data** · Docs: https://developers.binance.com/docs/binance-spot-api-docs/rest-api/market-data-endpoints · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/market_data/binance_collector.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /api/v3/ping` (https://developers.binance.com/docs/binance-spot-api-docs/rest-api/general-endpoints)
- `get_candles` — `GET /api/v3/klines` (https://developers.binance.com/docs/binance-spot-api-docs/rest-api/market-data-endpoints)
- `search_symbols` — `GET /api/v3/exchangeInfo` (https://developers.binance.com/docs/binance-spot-api-docs/rest-api/general-endpoints)
- ~~`get_series`~~ not offered: No named time series on the spot market-data API (funding/open interest live on the futures hosts, which this entry does not cover).
- ~~`get_news`~~ not offered: No news endpoint on this API.

## Credentials

None.

## Run

    uvx platform-mcp-hub serve binance_collector          # Python
    npx -y platform-mcp-hub serve binance_collector       # TypeScript
    claude mcp add binance_collector -- uvx platform-mcp-hub serve binance_collector

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/binance_collector-mcp`. Python and TypeScript serve identical tools.
