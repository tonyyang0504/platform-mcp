# Coinbase Exchange MCP server

Category: **trading** · Docs: https://docs.cdp.coinbase.com/exchange/reference/exchangerestapi_getproducts · Verified: 2026-10-01

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/trading/coinbase_exchange.json`; edit the catalog, not this file.

## Tools

- `list_markets` — `GET /products` (https://docs.cdp.coinbase.com/exchange/reference/exchangerestapi_getproducts)
- `get_ticker` — `GET /products/{symbol}/ticker` (https://docs.cdp.coinbase.com/exchange/reference/exchangerestapi_getproductticker)
- `get_candles` — `GET /products/{symbol}/candles` (https://docs.cdp.coinbase.com/exchange/reference/exchangerestapi_getproductcandles)
- ~~`me`~~ not offered: Private endpoints need CB-ACCESS-KEY, an HMAC-SHA256 CB-ACCESS-SIGN and a passphrase; public-data entry only.
- ~~`get_balances`~~ not offered: GET /accounts needs an API key; public-data entry only.
- ~~`list_orders`~~ not offered: GET /orders needs an API key; public-data entry only.
- ~~`place_order`~~ not offered: POST /orders needs an API key and spends money; not mapped.
- ~~`cancel_order`~~ not offered: DELETE /orders/{order_id} needs an API key; not mapped.

## Credentials

None.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve coinbase_exchange   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve coinbase_exchange
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve coinbase_exchange   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/coinbase_exchange-mcp`. Python and TypeScript serve identical tools.
