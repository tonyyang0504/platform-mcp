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

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve mercado_bitcoin   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve mercado_bitcoin
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve mercado_bitcoin   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/mercado_bitcoin-mcp`. Python and TypeScript serve identical tools.
