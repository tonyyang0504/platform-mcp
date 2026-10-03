# Reverb MCP server

Category: **ecommerce_channels** · Docs: https://www.reverb.com/page/api · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_channels/reverb.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /my/account` (https://www.reverb-api.com/docs/account-details)
- `update_listing` — `PUT /listings/{listing_id}` (https://www.reverb-api.com/docs/updating-your-listing)
- `set_inventory` — `PUT /listings/{listing_id}` (https://www.reverb-api.com/docs/create-listings)
- `end_listing` — `PUT /my/listings/{listing_id}/state/end` (https://www.reverb-api.com/docs/updating-your-listing)
- `list_orders` — `GET /my/orders/selling/{status}` (https://www.reverb-api.com/docs/retrieve-orders)
- `mark_shipped` — `POST /my/orders/selling/{order_id}/ship` (https://www.reverb-api.com/docs/ship-orders)
- ~~`create_listing`~~ not offered: POST /api/listings needs categories[{uuid}] and condition {uuid} from the Reverb taxonomies (plus make/model and shipping profile or rates) before a draft can be published; the vocabulary has no category or condition.

## Credentials

- `PLATFORM_MCP_REVERB_TOKEN` — Reverb Personal Access Token (My Profile > API & Integrations > Generate New Token) with scopes public, read_listings, write_listings, read_orders, write_orders; personal tokens do not expire. Sent as Authorization: Bearer.
- `PLATFORM_MCP_REVERB_CURRENCY` — Currency of your listing prices, e.g. USD; required when update_listing sends a price.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve reverb   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve reverb
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve reverb   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/reverb-mcp`. Python and TypeScript serve identical tools.
