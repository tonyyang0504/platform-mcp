# MEXC (spot) MCP server

Category: **trading** · Docs: https://mexcdevelop.github.io/apidocs/spot_v3_en/ · Verified: 2026-10-01

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/trading/mexc.json`; edit the catalog, not this file.

## Tools

- `list_markets` — `GET /api/v3/exchangeInfo` (https://mexcdevelop.github.io/apidocs/spot_v3_en/#exchange-information)
- `get_ticker` — `GET /api/v3/ticker/24hr` (https://mexcdevelop.github.io/apidocs/spot_v3_en/#24hr-ticker-price-change-statistics)
- `get_candles` — `GET /api/v3/klines` (https://mexcdevelop.github.io/apidocs/spot_v3_en/#kline-candlestick-data)
- ~~`me`~~ not offered: Account endpoints need X-MEXC-APIKEY and an HMAC-SHA256 signature over the query (the collection's {{signature}}/{{timestamp}}); public-data entry only.
- ~~`get_balances`~~ not offered: GET /api/v3/account is signed; public-data entry only.
- ~~`list_orders`~~ not offered: GET /api/v3/openOrders is signed; public-data entry only.
- ~~`place_order`~~ not offered: POST /api/v3/order is signed and spends money; not mapped.
- ~~`cancel_order`~~ not offered: DELETE /api/v3/order is signed; not mapped.

## Credentials

None.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve mexc   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve mexc
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve mexc   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/mexc-mcp`. Python and TypeScript serve identical tools.
