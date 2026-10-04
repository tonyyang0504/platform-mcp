# Kalshi (event contracts) MCP server

Category: **trading** · Docs: https://docs.kalshi.com/api-reference/market/get-markets · Verified: 2026-10-01

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/trading/kalshi.json`; edit the catalog, not this file.

## Tools

- `list_markets` — `GET /markets` (https://docs.kalshi.com/api-reference/market/get-markets)
- `get_ticker` — `GET /markets/{symbol}` (https://docs.kalshi.com/api-reference/market/get-market)
- ~~`me`~~ not offered: Portfolio endpoints need an API key id and an RSA-PSS signature (KALSHI-ACCESS-KEY/SIGNATURE/TIMESTAMP); public-data entry only.
- ~~`get_candles`~~ not offered: GET /series/{series_ticker}/markets/{ticker}/candlesticks requires the series ticker and a start_ts/end_ts window, which trading.get_candles does not take; not mapped rather than guessing a window.
- ~~`get_balances`~~ not offered: GET /portfolio/balance needs a signed key; public-data entry only.
- ~~`list_orders`~~ not offered: GET /portfolio/orders needs a signed key; public-data entry only.
- ~~`place_order`~~ not offered: POST /portfolio/orders needs a signed key and spends money; not mapped.
- ~~`cancel_order`~~ not offered: DELETE /portfolio/orders/{order_id} needs a signed key; not mapped.

## Credentials

None.

## Run

    uvx platform-mcp-hub serve kalshi          # Python
    npx -y platform-mcp-hub serve kalshi       # TypeScript
    claude mcp add kalshi -- uvx platform-mcp-hub serve kalshi

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/kalshi-mcp`. Python and TypeScript serve identical tools.
