# Deribit options API MCP server

Category: **market_data** · Docs: https://docs.deribit.com/ · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/market_data/deribit_collector.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /public/test` (https://docs.deribit.com/api-reference/supporting/public-test)
- `search_symbols` — `GET /public/get_instruments` (https://docs.deribit.com/api-reference/market-data/public-get_instruments)
- ~~`get_candles`~~ not offered: public/get_tradingview_chart_data (instrument_name, start_timestamp, end_timestamp in ms, resolution) returns parallel arrays result.ticks[]/open[]/high[]/low[]/close[]/volume[] rather than one record per candle; the runtime cannot zip parallel arrays.
- ~~`get_series`~~ not offered: public/get_funding_rate_history and get_historical_volatility need integer-millisecond timestamps and return positional/parallel rows; not mappable by the runtime.
- ~~`get_news`~~ not offered: No news endpoint on this API.

## Credentials

None.

## Run

    uvx platform-mcp-hub serve deribit_collector          # Python
    npx -y platform-mcp-hub serve deribit_collector       # TypeScript
    claude mcp add deribit_collector -- uvx platform-mcp-hub serve deribit_collector

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/deribit_collector-mcp`. Python and TypeScript serve identical tools.
