# Poe (Quora) MCP server

Category: **marketplaces** · Docs: https://creator.poe.com/docs · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/marketplaces/poe.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /bots` (https://creator.poe.com/api-reference/listBots)
- `list_products` — `GET /bots` (https://creator.poe.com/api-reference/listBots)
- ~~`get_product`~~ not offered: No GET /bots/{handle} is documented; list_products returns every bot's full record.
- ~~`create_product`~~ not offered: POST /bots needs handle plus api_bot_settings {model_name, base_url, api_key, api_type} of the upstream model server (https://creator.poe.com/api-reference/createBot); a name/price/currency product cannot express it.
- ~~`update_price`~~ not offered: Bot pricing is two per-token dollar strings (pricing {prompt, completion}) set by PATCH /bots/{handle}; a single major-unit price per product has no faithful mapping.
- ~~`list_sales`~~ not offered: No sales endpoint: 'earnings' are shown on the Creators page / help centre only (https://creator.poe.com/docs/resources/creator-monetization).
- ~~`get_sales_stats`~~ not offered: Earnings are dashboard-only (creator-monetization page); no stats endpoint.
- ~~`list_refunds`~~ not offered: No refunds concept or endpoint in the Bots API.
- ~~`refund`~~ not offered: No refunds concept or endpoint in the Bots API.

## Credentials

- `PLATFORM_MCP_POE_API_KEY` — Poe API key (poe.com/api_key).

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve poe   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve poe
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve poe   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/poe-mcp`. Python and TypeScript serve identical tools.
