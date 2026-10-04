# Binance COIN-M Futures MCP server

Category: **trading** · Docs: https://developers.binance.com/docs/derivatives/coin-margined-futures/general-info · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/trading/binance_cm.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /dapi/v1/account` (https://developers.binance.com/docs/derivatives/coin-margined-futures/account/rest-api)
- `list_markets` — `GET /dapi/v1/exchangeInfo` (https://developers.binance.com/docs/derivatives/coin-margined-futures/market-data/rest-api)
- `get_ticker` — `GET /dapi/v1/ticker/24hr` (https://developers.binance.com/docs/derivatives/coin-margined-futures/market-data/rest-api)
- `get_candles` — `GET /dapi/v1/klines` (https://developers.binance.com/docs/derivatives/coin-margined-futures/market-data/rest-api)
- `get_balances` — `GET /dapi/v1/balance` (https://developers.binance.com/docs/derivatives/coin-margined-futures/account/rest-api)
- `list_orders` — `GET /dapi/v1/openOrders` (https://developers.binance.com/docs/derivatives/coin-margined-futures/trade/rest-api)
- `place_order` — `POST /dapi/v1/order` (https://developers.binance.com/docs/derivatives/coin-margined-futures/trade/rest-api)
- `cancel_order` — `DELETE /dapi/v1/order` (https://developers.binance.com/docs/derivatives/coin-margined-futures/trade/rest-api)

## Credentials

- `PLATFORM_MCP_BINANCE_CM_API_KEY` — Binance API key (sent as X-MBX-APIKEY). Create it under API Management with withdrawals OFF; restrict it to your IP. Futures testnet: create a key at https://testnet.binancefuture.com and point adapter.base_url there (testnet keys only work on the testnet host).
- `PLATFORM_MCP_BINANCE_CM_API_SECRET` — The key's HMAC secret: signs every request (HMAC-SHA256 hex over the exact query string, appended as `signature` after `timestamp`). Never sent on the wire.

## Run

    uvx platform-mcp-hub serve binance_cm          # Python
    npx -y platform-mcp-hub serve binance_cm       # TypeScript
    claude mcp add binance_cm -- uvx platform-mcp-hub serve binance_cm

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/binance_cm-mcp`. Python and TypeScript serve identical tools.
