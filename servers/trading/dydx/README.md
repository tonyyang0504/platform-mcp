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

    uvx platform-mcp-hub serve dydx          # Python
    npx -y platform-mcp-hub serve dydx       # TypeScript
    claude mcp add dydx -- uvx platform-mcp-hub serve dydx

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/dydx-mcp`. Python and TypeScript serve identical tools.
