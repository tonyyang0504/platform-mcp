# Frankfurter (exchange rates) MCP server

Category: **market_data** · Docs: https://frankfurter.dev/ · Verified: 2026-09-27

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/market_data/frankfurter.json`; edit the catalog, not this file.

## Tools

- `search_symbols` — `GET /currencies` (https://api.frankfurter.dev/v2/openapi.json)
- `get_series` — `GET /rates` (https://api.frankfurter.dev/v2/openapi.json)
- ~~`me`~~ not offered: No accounts or keys: the API is public ('no API key required', https://frankfurter.dev/).
- ~~`get_candles`~~ not offered: Reference rates only: one blended rate per currency per date, no OHLC candles (GET /rates returns {date, base, quote, rate}).
- ~~`get_news`~~ not offered: The API serves exchange rates only; there is no news endpoint in the spec.

## Credentials

- `PLATFORM_MCP_FRANKFURTER_BASE_CURRENCY` — ISO 4217 base currency for get_series (the API's `base`, default EUR per the spec).

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve frankfurter   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve frankfurter
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve frankfurter   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/frankfurter-mcp`. Python and TypeScript serve identical tools.
