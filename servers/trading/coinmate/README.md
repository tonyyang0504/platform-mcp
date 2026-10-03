# Coinmate MCP server

Category: **trading** · Docs: https://coinmate.docs.apiary.io/ · Verified: 2026-10-01

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/trading/coinmate.json`; edit the catalog, not this file.

## Tools

- `list_markets` — `GET /tradingPairs` (https://coinmate.docs.apiary.io/#reference/trading-pairs/get-trading-pairs/get)
- `get_ticker` — `GET /ticker` (https://coinmate.docs.apiary.io/#reference/ticker/get-ticker/get)
- ~~`me`~~ not offered: Private operations are signed (HMAC-SHA256 over nonce + clientId + publicKey); public-data entry only.
- ~~`get_candles`~~ not offered: No OHLC endpoint is documented (only transactions and the order book).
- ~~`get_balances`~~ not offered: POST /balances is a signed private operation; public-data entry only.
- ~~`list_orders`~~ not offered: POST /openOrders is a signed private operation; public-data entry only.
- ~~`place_order`~~ not offered: POST /buyLimit and /sellLimit are signed and spend money; not mapped.
- ~~`cancel_order`~~ not offered: POST /cancelOrder is signed; not mapped.

## Credentials

None.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve coinmate   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve coinmate
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve coinmate   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/coinmate-mcp`. Python and TypeScript serve identical tools.
