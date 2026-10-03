# dYdX v4 (indexer) MCP server

Category: **trading** · Docs: https://docs.dydx.xyz/indexer-client/http · Verified: 2026-10-01

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/trading/dydx.json`; edit the catalog, not this file.

## Tools

- `list_markets` — `GET /perpetualMarkets` (https://docs.dydx.xyz/indexer-client/http#get-perpetual-markets)
- `get_ticker` — `GET /perpetualMarkets` (https://docs.dydx.xyz/indexer-client/http#get-perpetual-markets)
- `get_candles` — `GET /candles/perpetualMarkets/{symbol}` (https://docs.dydx.xyz/indexer-client/http#get-candles)
- ~~`me`~~ not offered: dYdX accounts are chain addresses; there is no authenticated identity on the indexer.
- ~~`get_balances`~~ not offered: Subaccount balances need a chain address (GET /addresses/{address}/subaccountNumber/{n}), which is not an input of trading.get_balances; not mapped.
- ~~`list_orders`~~ not offered: GET /orders needs an address and subaccount; not an input of the verb.
- ~~`place_order`~~ not offered: Orders are signed chain transactions (MsgPlaceOrder), not indexer HTTP calls.
- ~~`cancel_order`~~ not offered: Cancellations are signed chain transactions (MsgCancelOrder), not indexer HTTP calls.

## Credentials

None.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve dydx   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve dydx
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve dydx   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/dydx-mcp`. Python and TypeScript serve identical tools.
