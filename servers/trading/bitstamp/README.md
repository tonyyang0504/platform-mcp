# Bitstamp MCP server

Category: **trading** · Docs: https://www.bitstamp.net/api/ · Verified: 2026-09-27

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/trading/bitstamp.json`; edit the catalog, not this file.

## Tools

- `list_markets` — `GET /markets/` (https://www.bitstamp.net/api/#tag/Market-info/operation/GetMarkets)
- `get_ticker` — `GET /ticker/{symbol}/` (https://www.bitstamp.net/api/#tag/Tickers/operation/GetMarketTicker)
- `get_candles` — `GET /ohlc/{symbol}/` (https://www.bitstamp.net/api/#tag/Market-info/operation/GetOHLCData)
- ~~`me`~~ not offered: No keyless account endpoint; every account call needs the X-Auth API-key + HMAC-SHA256 X-Auth-Signature headers (security schemes in https://www.bitstamp.net/api/). This entry serves public market data only.
- ~~`get_balances`~~ not offered: POST /api/v2/account_balances/ requires the X-Auth / X-Auth-Signature authentication; no credentials available — public-data entry only.
- ~~`list_orders`~~ not offered: POST /api/v2/open_orders/ requires the X-Auth / X-Auth-Signature authentication; public-data entry only.
- ~~`place_order`~~ not offered: POST /api/v2/buy/{market_symbol}/ and /api/v2/sell/{market_symbol}/ require authentication and spend money; not mapped in this public-data entry.
- ~~`cancel_order`~~ not offered: POST /api/v2/cancel_order/ requires the X-Auth / X-Auth-Signature authentication; not mapped in this public-data entry.

## Credentials

None.

## Run

    uvx platform-mcp-hub serve bitstamp          # Python
    npx -y platform-mcp-hub serve bitstamp       # TypeScript
    claude mcp add bitstamp -- uvx platform-mcp-hub serve bitstamp

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/bitstamp-mcp`. Python and TypeScript serve identical tools.
