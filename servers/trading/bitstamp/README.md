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

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve bitstamp   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve bitstamp
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve bitstamp   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/bitstamp-mcp`. Python and TypeScript serve identical tools.
