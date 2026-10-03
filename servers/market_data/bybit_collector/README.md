# Bybit V5 public REST MCP server

Category: **market_data** · Docs: https://bybit-exchange.github.io/docs/v5/market/ · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/market_data/bybit_collector.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /v5/market/time` (https://bybit-exchange.github.io/docs/v5/market/time)
- `get_candles` — `GET /v5/market/kline` (https://bybit-exchange.github.io/docs/v5/market/kline)
- `search_symbols` — `GET /v5/market/instruments-info` (https://bybit-exchange.github.io/docs/v5/market/instrument)
- ~~`get_series`~~ not offered: Funding-rate history (GET /v5/market/funding/history) and open interest (GET /v5/market/open-interest) are documented, but the market_data get_series input has no symbol/category split and no interval, and both need epoch-millisecond start/end; not mapped in this pass.
- ~~`get_news`~~ not offered: No news endpoint on this API.

## Credentials

None.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve bybit_collector   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve bybit_collector
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve bybit_collector   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/bybit_collector-mcp`. Python and TypeScript serve identical tools.
