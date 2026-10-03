# Circle MCP server

Category: **marketplaces** · Docs: https://api.circle.so · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/marketplaces/circle.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /api/admin/v2/community` (https://api-headless.circle.so/api/admin/v2/swagger.yaml)
- `list_sales` — `GET /api/admin/v2/community_member_charges` (https://api-headless.circle.so/api/admin/v2/swagger.yaml)
- `list_refunds` — `GET /api/admin/v2/community_member_charges` (https://api-headless.circle.so/api/admin/v2/swagger.yaml)
- `refund` — `POST /api/admin/v2/community_member_charges/{sale_id}/refund` (https://api-headless.circle.so/api/admin/v2/swagger.yaml)
- ~~`list_products`~~ not offered: Admin API v2 exposes paywalls only as DELETE /api/admin/v2/paywalls/{id} (plus paywall groups, coupons and affiliates); there is no endpoint that lists paywalls — they are managed in the community's Paywalls settings UI.
- ~~`get_product`~~ not offered: No GET /api/admin/v2/paywalls/{id}: the only paywall operation is DELETE, so a paywall cannot be read through the API (paywall_id / paywall_name appear on charge and subscription rows).
- ~~`create_product`~~ not offered: No paywall creation endpoint in Admin API v2 (only DELETE /api/admin/v2/paywalls/{id}); paywalls and their prices are created in the community settings UI.
- ~~`update_price`~~ not offered: Paywall prices (paywall_price_id, paywall_price_type, paywall_price_interval on charge rows) have no create/update endpoint in Admin API v2.
- ~~`get_sales_stats`~~ not offered: No revenue-totals endpoint: POST /api/admin/v2/community_member_charges/export creates a background CSV export that is e-mailed to the admin, which the runtime cannot map; totals must be summed from list_sales rows.

## Credentials

- `PLATFORM_MCP_CIRCLE_ADMIN_TOKEN` — Circle Admin API v2 token (community Settings > Developers > Tokens, type Admin V2; Business plan or above) sent as Authorization: Bearer per the Admin API quick start (the Swagger spec documents the same header as 'Token <token>').

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve circle   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve circle
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve circle   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/circle-mcp`. Python and TypeScript serve identical tools.
