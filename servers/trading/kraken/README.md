# Kraken (spot) MCP server

Category: **trading** · Docs: https://docs.kraken.com/api-reference/market-data/get-ticker-information · Verified: 2026-10-01

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/trading/kraken.json`; edit the catalog, not this file.

## Tools

- `list_markets` — `GET /public/AssetPairs` (https://docs.kraken.com/api-reference/market-data/get-tradable-asset-pairs)
- `get_ticker` — `GET /public/Ticker` (https://docs.kraken.com/api-reference/market-data/get-ticker-information)
- `get_candles` — `GET /public/OHLC` (https://docs.kraken.com/api-reference/market-data/get-ohlc-data)
- ~~`me`~~ not offered: Account endpoints (/private/*) need API-Key + API-Sign (HMAC-SHA512 over nonce and payload); public-data entry only.
- ~~`get_balances`~~ not offered: POST /private/Balance needs an API key with 'Funds permissions - Query'; public-data entry only.
- ~~`list_orders`~~ not offered: POST /private/OpenOrders needs an API key; public-data entry only.
- ~~`place_order`~~ not offered: POST /private/AddOrder needs an API key and spends money; not mapped in this public-data entry.
- ~~`cancel_order`~~ not offered: POST /private/CancelOrder needs an API key; not mapped in this public-data entry.

## Credentials

None.

## Run

    uvx platform-mcp-hub serve kraken          # Python
    npx -y platform-mcp-hub serve kraken       # TypeScript
    claude mcp add kraken -- uvx platform-mcp-hub serve kraken

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/kraken-mcp`. Python and TypeScript serve identical tools.
