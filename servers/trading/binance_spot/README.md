# Binance Spot MCP server

Category: **trading** · Docs: https://developers.binance.com/docs/binance-spot-api-docs/rest-api · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/trading/binance_spot.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /api/v3/account` (https://developers.binance.com/docs/binance-spot-api-docs/rest-api/account-endpoints)
- `list_markets` — `GET /api/v3/exchangeInfo` (https://developers.binance.com/docs/binance-spot-api-docs/rest-api/general-endpoints)
- `get_ticker` — `GET /api/v3/ticker/24hr` (https://developers.binance.com/docs/binance-spot-api-docs/rest-api/market-data-endpoints)
- `get_candles` — `GET /api/v3/klines` (https://developers.binance.com/docs/binance-spot-api-docs/rest-api/market-data-endpoints)
- `get_balances` — `GET /api/v3/account` (https://developers.binance.com/docs/binance-spot-api-docs/rest-api/account-endpoints)
- `list_orders` — `GET /api/v3/openOrders` (https://developers.binance.com/docs/binance-spot-api-docs/rest-api/account-endpoints)
- `place_order` — `POST /api/v3/order` (https://developers.binance.com/docs/binance-spot-api-docs/rest-api/trading-endpoints)
- `cancel_order` — `DELETE /api/v3/order` (https://developers.binance.com/docs/binance-spot-api-docs/rest-api/trading-endpoints)

## Credentials

- `PLATFORM_MCP_BINANCE_SPOT_API_KEY` — Binance API key (sent as X-MBX-APIKEY). Create it under API Management with withdrawals OFF; restrict it to your IP. For the spot testnet create a separate key at https://testnet.binance.vision and point adapter.base_url at https://testnet.binance.vision (the testnet key does not work on api.binance.com and vice versa).
- `PLATFORM_MCP_BINANCE_SPOT_API_SECRET` — The key's HMAC secret: signs every request (HMAC-SHA256 hex over the exact query string, appended as `signature` after `timestamp`). Never sent on the wire.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve binance_spot   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve binance_spot
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve binance_spot   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/binance_spot-mcp`. Python and TypeScript serve identical tools.
