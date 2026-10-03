# Hyperliquid REST MCP server

Category: **market_data** · Docs: https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/market_data/hyperliquid_collector.json`; edit the catalog, not this file.

## Tools

- `me` — `POST /info` (https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint/perpetuals)
- `search_symbols` — `POST /info` (https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint/perpetuals)
- ~~`get_candles`~~ not offered: candleSnapshot is documented as {"type": "candleSnapshot", "req": {coin, interval, startTime, endTime}} with startTime/endTime REQUIRED epoch-millisecond integers in the JSON body (the runtime's dotted body keys could build `req`, but the vocabulary passes start/end as strings and the runtime cannot coerce them to integers) — a runtime type-cast expression is needed. Response rows {t, T, s, i, o, c, h, l, v, n} would map.
- ~~`get_series`~~ not offered: fundingHistory {"type", coin, startTime} likewise needs an integer-millisecond startTime in the body (see get_candles).
- ~~`get_news`~~ not offered: No news endpoint on this API.

## Credentials

None.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve hyperliquid_collector   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve hyperliquid_collector
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve hyperliquid_collector   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/hyperliquid_collector-mcp`. Python and TypeScript serve identical tools.
