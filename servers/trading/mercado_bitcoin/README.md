# Mercado Bitcoin (public market data) MCP server

Category: **trading** · Docs: https://api.mercadobitcoin.net/api/v4/docs · Verified: 2026-09-27

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/trading/mercado_bitcoin.json`; edit the catalog, not this file.

## Tools

- `list_markets` — `GET /symbols` (https://api.mercadobitcoin.net/api/v4/docs)
- `get_ticker` — `GET /tickers` (https://api.mercadobitcoin.net/api/v4/docs)
- `get_candles` — `GET /candles` (https://api.mercadobitcoin.net/api/v4/docs)
- ~~`me`~~ not offered: Account endpoints (GET /accounts) need a bearer token from POST /oauth2/token with an API key; this entry serves the keyless public data only.
- ~~`get_balances`~~ not offered: GET /accounts/{accountId}/balances needs the Bearer token (securityDefinitions.Bearer); public-data entry only.
- ~~`list_orders`~~ not offered: GET /accounts/{accountId}/orders needs the Bearer token; public-data entry only.
- ~~`place_order`~~ not offered: POST /accounts/{accountId}/{symbol}/orders needs the Bearer token and spends money; not mapped in this public-data entry.
- ~~`cancel_order`~~ not offered: DELETE /accounts/{accountId}/{symbol}/orders/{orderId} needs the Bearer token; not mapped in this public-data entry.

## Credentials

None.

## Run

    uvx platform-mcp-hub serve mercado_bitcoin          # Python
    npx -y platform-mcp-hub serve mercado_bitcoin       # TypeScript
    claude mcp add mercado_bitcoin -- uvx platform-mcp-hub serve mercado_bitcoin

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/mercado_bitcoin-mcp`. Python and TypeScript serve identical tools.
