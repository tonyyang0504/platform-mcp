# KuCoin (spot) MCP server

Category: **trading** · Docs: https://www.kucoin.com/docs-new/rest/spot-trading/market-data/get-all-symbols · Verified: 2026-10-01

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/trading/kucoin.json`; edit the catalog, not this file.

## Tools

- `list_markets` — `GET /api/v2/symbols` (https://www.kucoin.com/docs-new/rest/spot-trading/market-data/get-all-symbols)
- `get_ticker` — `GET /api/v1/market/stats` (https://www.kucoin.com/docs-new/rest/spot-trading/market-data/get-24hr-stats)
- `get_candles` — `GET /api/v1/market/candles` (https://www.kucoin.com/docs-new/rest/spot-trading/market-data/get-klines)
- ~~`me`~~ not offered: Account endpoints need KC-API-KEY, an HMAC-SHA256 KC-API-SIGN and an encrypted passphrase; public-data entry only.
- ~~`get_balances`~~ not offered: GET /api/v1/accounts needs an API key; public-data entry only.
- ~~`list_orders`~~ not offered: GET /api/v1/orders needs an API key; public-data entry only.
- ~~`place_order`~~ not offered: POST /api/v1/orders needs an API key and spends money; not mapped.
- ~~`cancel_order`~~ not offered: DELETE /api/v1/orders/{orderId} needs an API key; not mapped.

## Credentials

None.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve kucoin   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve kucoin
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve kucoin   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/kucoin-mcp`. Python and TypeScript serve identical tools.
