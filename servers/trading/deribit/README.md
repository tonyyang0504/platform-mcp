# Deribit Options & Futures MCP server

Category: **trading** · Docs: https://docs.deribit.com/articles/authentication · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/trading/deribit.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /private/get_account_summaries` (https://docs.deribit.com/api-reference/account-management/private-get_account_summaries)
- `list_markets` — `GET /public/get_instruments` (https://docs.deribit.com/api-reference/market-data/public-get_instruments)
- `get_ticker` — `GET /public/ticker` (https://docs.deribit.com/api-reference/market-data/public-ticker)
- `get_balances` — `GET /private/get_account_summaries` (https://docs.deribit.com/api-reference/account-management/private-get_account_summaries)
- `list_orders` — `GET /private/get_open_orders` (https://docs.deribit.com/api-reference/trading/private-get_open_orders)
- `place_order` — `GET /private/{order_side}` (https://docs.deribit.com/api-reference/trading/private-buy)
- `cancel_order` — `GET /private/cancel` (https://docs.deribit.com/api-reference/trading/private-cancel)
- ~~`get_candles`~~ not offered: public/get_tradingview_chart_data returns columnar arrays (result.ticks[], result.open[], result.high[] ...) rather than one record per candle, and start_timestamp/end_timestamp are mandatory; the result mapper reads row lists and the vocabulary carries no time range.

## Credentials

- `PLATFORM_MCP_DERIBIT_CLIENT_ID` — Client ID of a Deribit API key (Account > API). Give it trade:read_write and NOT wallet:read_write or account:read_write. A test-environment key comes from https://test.deribit.com and works only against https://test.deribit.com/api/v2 (set adapter.base_url to it).
- `PLATFORM_MCP_DERIBIT_CLIENT_SECRET` — The key's Client Secret; sent as HTTP Basic credentials (Authorization: Basic base64(client_id:client_secret)) on each request over TLS.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve deribit   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve deribit
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve deribit   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/deribit-mcp`. Python and TypeScript serve identical tools.
