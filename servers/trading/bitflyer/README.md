# bitFlyer Lightning MCP server

Category: **trading** · Docs: https://lightning.bitflyer.com/docs?lang=ja · Verified: 2026-10-01

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/trading/bitflyer.json`; edit the catalog, not this file.

## Tools

- `list_markets` — `GET /v1/getmarkets` (https://lightning.bitflyer.com/docs?lang=ja#マーケットの一覧)
- `get_ticker` — `GET /v1/getticker` (https://lightning.bitflyer.com/docs?lang=ja#ticker)
- ~~`me`~~ not offered: Private API calls need ACCESS-KEY and an HMAC-SHA256 ACCESS-SIGN; public-data entry only.
- ~~`get_candles`~~ not offered: The public HTTP API has no OHLC endpoint (only executions and the board); not mapped.
- ~~`get_balances`~~ not offered: GET /v1/me/getbalance needs an API key; public-data entry only.
- ~~`list_orders`~~ not offered: GET /v1/me/getchildorders needs an API key; public-data entry only.
- ~~`place_order`~~ not offered: POST /v1/me/sendchildorder needs an API key and spends money; not mapped.
- ~~`cancel_order`~~ not offered: POST /v1/me/cancelchildorder needs an API key; not mapped.

## Credentials

None.

## Run

    uvx platform-mcp-hub serve bitflyer          # Python
    npx -y platform-mcp-hub serve bitflyer       # TypeScript
    claude mcp add bitflyer -- uvx platform-mcp-hub serve bitflyer

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/bitflyer-mcp`. Python and TypeScript serve identical tools.
