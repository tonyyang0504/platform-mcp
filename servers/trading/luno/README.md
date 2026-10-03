# Luno MCP server

Category: **trading** · Docs: https://www.luno.com/en/developers/api · Verified: 2026-09-27

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/trading/luno.json`; edit the catalog, not this file.

## Tools

- `list_markets` — `GET /api/exchange/1/markets` (https://www.luno.com/en/developers/api#tag/Market/operation/Markets)
- `get_ticker` — `GET /api/1/ticker` (https://www.luno.com/en/developers/api#tag/Market/operation/GetTicker)
- ~~`me`~~ not offered: No public identity endpoint; every account call 'requires your application to authenticate itself ... using an API key' (HTTP basic auth). Public-data entry only.
- ~~`get_candles`~~ not offered: GET /api/exchange/1/candles lists 'Permissions required: MP_None', i.e. it needs an API key (live 2026-09-27: 401 ErrUnauthorized without one); no credentials in this public-data entry.
- ~~`get_balances`~~ not offered: GET /api/1/balance requires an API key with 'Perm_R_Balance'; public-data entry only.
- ~~`list_orders`~~ not offered: GET /api/1/listorders requires an API key with 'Perm_R_Orders'; public-data entry only.
- ~~`place_order`~~ not offered: POST /api/1/postorder and /api/1/marketorder require an API key with 'Perm_W_Orders' and spend money; not mapped in this public-data entry.
- ~~`cancel_order`~~ not offered: POST /api/1/stoporder requires an API key with 'Perm_W_Orders'; not mapped in this public-data entry.

## Credentials

None.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve luno   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve luno
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve luno   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/luno-mcp`. Python and TypeScript serve identical tools.
