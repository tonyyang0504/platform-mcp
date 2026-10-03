# Bybit (Unified) MCP server

Category: **trading** · Docs: https://bybit-exchange.github.io/docs/v5/guide · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/trading/bybit.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /v5/user/query-api` (https://bybit-exchange.github.io/docs/v5/user/apikey-info)
- `list_markets` — `GET /v5/market/instruments-info` (https://bybit-exchange.github.io/docs/v5/market/instrument)
- `get_ticker` — `GET /v5/market/tickers` (https://bybit-exchange.github.io/docs/v5/market/tickers)
- `get_candles` — `GET /v5/market/kline` (https://bybit-exchange.github.io/docs/v5/market/kline)
- `get_balances` — `GET /v5/account/wallet-balance` (https://bybit-exchange.github.io/docs/v5/account/wallet-balance)
- `list_orders` — `GET /v5/order/realtime` (https://bybit-exchange.github.io/docs/v5/order/open-order)
- `place_order` — `POST /v5/order/create` (https://bybit-exchange.github.io/docs/v5/order/create-order)
- `cancel_order` — `POST /v5/order/cancel` (https://bybit-exchange.github.io/docs/v5/order/cancel-order)

## Credentials

- `PLATFORM_MCP_BYBIT_API_KEY` — Bybit API key (system-generated HMAC key) with Read + Trade (Spot/Contract) and NO Wallet/Transfer/Withdraw permission. Testnet keys come from https://testnet.bybit.com and work only against https://api-testnet.bybit.com (set adapter.base_url to it).
- `PLATFORM_MCP_BYBIT_API_SECRET` — The key's secret: HMAC-SHA256 over timestamp + api_key + recv_window (5000) + query string (GET) or JSON body (POST), sent as X-BAPI-SIGN. Never sent on the wire.
- `PLATFORM_MCP_BYBIT_CATEGORY` — Bybit product category every tool works on: `spot` or `linear` (USDT/USDC perpetuals and futures).

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve bybit   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve bybit
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve bybit   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/bybit-mcp`. Python and TypeScript serve identical tools.
