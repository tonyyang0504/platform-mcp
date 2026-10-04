# Binance USD-M Futures MCP server

Category: **trading** · Docs: https://developers.binance.com/docs/derivatives/usds-margined-futures/general-info · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/trading/binance.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /fapi/v1/accountConfig` (https://developers.binance.com/docs/derivatives/usds-margined-futures/account/rest-api)
- `list_markets` — `GET /fapi/v1/exchangeInfo` (https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api)
- `get_ticker` — `GET /fapi/v1/ticker/24hr` (https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api)
- `get_candles` — `GET /fapi/v1/klines` (https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api)
- `get_balances` — `GET /fapi/v3/balance` (https://developers.binance.com/docs/derivatives/usds-margined-futures/account/rest-api)
- `list_orders` — `GET /fapi/v1/openOrders` (https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api)
- `place_order` — `POST /fapi/v1/order` (https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api)
- `cancel_order` — `DELETE /fapi/v1/order` (https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api)

## Credentials

- `PLATFORM_MCP_BINANCE_API_KEY` — Binance API key (sent as X-MBX-APIKEY). Create it under API Management with withdrawals OFF; restrict it to your IP. Futures testnet: create a key at https://testnet.binancefuture.com and point adapter.base_url there (testnet keys only work on the testnet host).
- `PLATFORM_MCP_BINANCE_API_SECRET` — The key's HMAC secret: signs every request (HMAC-SHA256 hex over the exact query string, appended as `signature` after `timestamp`). Never sent on the wire.

## Run

    uvx platform-mcp-hub serve binance          # Python
    npx -y platform-mcp-hub serve binance       # TypeScript
    claude mcp add binance -- uvx platform-mcp-hub serve binance

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/binance-mcp`. Python and TypeScript serve identical tools.
