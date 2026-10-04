# Upbit (업비트) MCP server

Category: **trading** · Docs: https://docs.upbit.com/kr/reference/list-trading-pairs · Verified: 2026-10-01

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/trading/upbit.json`; edit the catalog, not this file.

## Tools

- `list_markets` — `GET /v1/market/all` (https://docs.upbit.com/kr/reference/list-trading-pairs)
- `get_ticker` — `GET /v1/ticker` (https://docs.upbit.com/kr/reference/list-tickers)
- `get_candles` — `GET /v1/candles/{unit}` (https://docs.upbit.com/kr/reference/list-candles-minutes)
- ~~`me`~~ not offered: Exchange API calls need an access key and a JWT signed with the secret key; public-data entry only.
- ~~`get_balances`~~ not offered: GET /v1/accounts needs a JWT-authenticated key; public-data entry only.
- ~~`list_orders`~~ not offered: GET /v1/orders/open needs a JWT-authenticated key; public-data entry only.
- ~~`place_order`~~ not offered: POST /v1/orders needs a JWT-authenticated key and spends money; not mapped.
- ~~`cancel_order`~~ not offered: DELETE /v1/order needs a JWT-authenticated key; not mapped.

## Credentials

None.

## Run

    uvx platform-mcp-hub serve upbit          # Python
    npx -y platform-mcp-hub serve upbit       # TypeScript
    claude mcp add upbit -- uvx platform-mcp-hub serve upbit

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/upbit-mcp`. Python and TypeScript serve identical tools.
