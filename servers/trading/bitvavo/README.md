# Bitvavo MCP server

Category: **trading** · Docs: https://docs.bitvavo.com/docs/rest-api/introduction/ · Verified: 2026-09-27

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/trading/bitvavo.json`; edit the catalog, not this file.

## Tools

- `list_markets` — `GET /markets` (https://docs.bitvavo.com/docs/rest-api/get-markets/)
- `get_ticker` — `GET /ticker/24h` (https://docs.bitvavo.com/docs/rest-api/get-ticker-data-24-h/)
- `get_candles` — `GET /{symbol}/candles` (https://docs.bitvavo.com/docs/rest-api/get-candlestick-data/)
- ~~`me`~~ not offered: Account endpoints need an API key and an HMAC-SHA256 Bitvavo-Access-Signature (https://docs.bitvavo.com/docs/rest-api/introduction/); this entry serves the public market data only.
- ~~`get_balances`~~ not offered: GET /v2/balance requires the Bitvavo-Access-Key / Bitvavo-Access-Signature headers (https://docs.bitvavo.com/docs/rest-api/get-account-balance/); public-data entry only.
- ~~`list_orders`~~ not offered: GET /v2/ordersOpen requires authentication (https://docs.bitvavo.com/docs/rest-api/get-open-orders/); public-data entry only.
- ~~`place_order`~~ not offered: POST /v2/order requires authentication and spends money (https://docs.bitvavo.com/docs/rest-api/create-order/); not mapped in this public-data entry.
- ~~`cancel_order`~~ not offered: DELETE /v2/order requires authentication (https://docs.bitvavo.com/docs/rest-api/cancel-order/); not mapped in this public-data entry.

## Credentials

None.

## Run

    uvx platform-mcp-hub serve bitvavo          # Python
    npx -y platform-mcp-hub serve bitvavo       # TypeScript
    claude mcp add bitvavo -- uvx platform-mcp-hub serve bitvavo

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/bitvavo-mcp`. Python and TypeScript serve identical tools.
