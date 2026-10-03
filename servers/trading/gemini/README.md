# Gemini (spot) MCP server

Category: **trading** · Docs: https://docs.gemini.com/rest/market-data · Verified: 2026-10-01

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/trading/gemini.json`; edit the catalog, not this file.

## Tools

- `list_markets` — `GET /v1/symbols` (https://docs.gemini.com/rest/market-data#list-symbols)
- `get_ticker` — `GET /v1/pubticker/{symbol}` (https://docs.gemini.com/rest/market-data#ticker)
- `get_candles` — `GET /v2/candles/{symbol}/{interval}` (https://docs.gemini.com/rest/market-data#candles)
- ~~`me`~~ not offered: Private endpoints need an API key and an HMAC-SHA384 signature over a base64 payload (X-GEMINI-APIKEY/X-GEMINI-PAYLOAD/X-GEMINI-SIGNATURE); public-data entry only.
- ~~`get_balances`~~ not offered: POST /v1/balances needs an API key with the Fund Manager or Trader role; public-data entry only.
- ~~`list_orders`~~ not offered: POST /v1/orders needs an API key with the Trader role; public-data entry only.
- ~~`place_order`~~ not offered: POST /v1/order/new needs an API key and spends money; not mapped in this public-data entry.
- ~~`cancel_order`~~ not offered: POST /v1/order/cancel needs an API key; not mapped in this public-data entry.

## Credentials

None.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve gemini   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve gemini
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve gemini   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/gemini-mcp`. Python and TypeScript serve identical tools.
