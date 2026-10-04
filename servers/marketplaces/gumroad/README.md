# Gumroad MCP server

Category: **marketplaces** · Docs: https://gumroad.com/api · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/marketplaces/gumroad.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /user` (https://app.gumroad.com/api)
- `list_products` — `GET /products` (https://app.gumroad.com/api)
- `get_product` — `GET /products/{product_id}` (https://app.gumroad.com/api)
- `create_product` — `POST /products` (https://app.gumroad.com/api)
- `update_price` — `PUT /products/{product_id}` (https://app.gumroad.com/api)
- `list_sales` — `GET /sales` (https://app.gumroad.com/api)
- `refund` — `PUT /sales/{sale_id}/refund` (https://app.gumroad.com/api)
- ~~`get_sales_stats`~~ not offered: The public API reference documents only per-sale records (GET /sales, GET /sales/:id) and per-product sales_count / sales_usd_cents on GET /products; no revenue-totals endpoint is documented there.
- ~~`list_refunds`~~ not offered: No refunds endpoint: refunds and chargebacks are the refunded, partially_refunded, chargedback and disputed flags on the GET /sales rows (filter list_sales client-side).

## Credentials

- `PLATFORM_MCP_GUMROAD_ACCESS_TOKEN` — Gumroad access token (Settings > Advanced > Applications > Create application > Generate access token; scopes view_profile, edit_products, view_sales, edit_sales) sent as Authorization: Bearer. The API page's curl examples pass the same token as the access_token parameter instead.

## Run

    uvx platform-mcp-hub serve gumroad          # Python
    npx -y platform-mcp-hub serve gumroad       # TypeScript
    claude mcp add gumroad -- uvx platform-mcp-hub serve gumroad

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/gumroad-mcp`. Python and TypeScript serve identical tools.
