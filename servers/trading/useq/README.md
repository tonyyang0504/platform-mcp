# US Equities (Alpaca) MCP server

Category: **trading** · Docs: https://docs.alpaca.markets/docs/trading-api · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/trading/useq.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /v2/account` (https://docs.alpaca.markets/reference/getaccount-1)
- `list_markets` — `GET /v2/assets` (https://docs.alpaca.markets/reference/get-v2-assets-1)
- `get_ticker` — `GET https://data.alpaca.markets/v2/stocks/{symbol}/snapshot` (https://docs.alpaca.markets/reference/stocksnapshotsingle)
- `get_balances` — `GET /v2/positions` (https://docs.alpaca.markets/reference/getallopenpositions)
- `list_orders` — `GET /v2/orders` (https://docs.alpaca.markets/reference/getallorders-1)
- `place_order` — `POST /v2/orders` (https://docs.alpaca.markets/reference/postorder)
- `cancel_order` — `DELETE /v2/orders/{order_id}` (https://docs.alpaca.markets/reference/deleteorderbyorderid-1)
- ~~`get_candles`~~ not offered: Historical bars come from GET /v2/stocks/bars?symbols=, whose response keys bars by symbol ({bars: {AAPL: [...]}}) so the row path depends on the argument, and `start` defaults to the beginning of the current day (the vocabulary carries no time range).

## Credentials

- `PLATFORM_MCP_USEQ_API_KEY` — Alpaca API key id (APCA-API-KEY-ID). Paper keys (paper dashboard) work only on https://paper-api.alpaca.markets, the default here; live keys need adapter.base_url https://api.alpaca.markets.
- `PLATFORM_MCP_USEQ_API_SECRET` — Alpaca API secret key (APCA-API-SECRET-KEY).

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve useq   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve useq
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve useq   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/useq-mcp`. Python and TypeScript serve identical tools.
