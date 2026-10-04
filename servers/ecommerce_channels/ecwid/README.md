# Ecwid by Lightspeed MCP server

Category: **ecommerce_channels** · Docs: https://docs.ecwid.com/ · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_channels/ecwid.json`; edit the catalog, not this file.

## Tools

- `me` — `GET https://app.ecwid.com/api/v3/{store_id}/profile` (https://docs.ecwid.com/api-reference/rest-api/store-profile/get-store-profile)
- `create_listing` — `POST https://app.ecwid.com/api/v3/{store_id}/products` (https://docs.ecwid.com/api-reference/rest-api/products/create-product)
- `update_listing` — `PUT https://app.ecwid.com/api/v3/{store_id}/products/{listing_id}` (https://docs.ecwid.com/api-reference/rest-api/products/update-product)
- `end_listing` — `PUT https://app.ecwid.com/api/v3/{store_id}/products/{listing_id}` (https://docs.ecwid.com/api-reference/rest-api/products/update-product)
- `set_inventory` — `PUT https://app.ecwid.com/api/v3/{store_id}/products/{listing_id}` (https://docs.ecwid.com/api-reference/rest-api/products/update-product)
- `list_orders` — `GET https://app.ecwid.com/api/v3/{store_id}/orders` (https://docs.ecwid.com/api-reference/rest-api/orders/search-orders)
- `mark_shipped` — `PUT https://app.ecwid.com/api/v3/{store_id}/orders/{order_id}` (https://docs.ecwid.com/api-reference/rest-api/orders/update-order)
- ~~`listing_metrics`~~ not offered: No analytics endpoint in the Ecwid REST API (no product views / conversions); only order data is exposed.

## Credentials

- `PLATFORM_MCP_ECWID_TOKEN` — Secret token of a custom app (Ecwid admin > Apps > Develop Apps > app Details; scopes read_catalog, create_catalog, update_catalog, read_orders, update_orders); non-expiring, sent as `Authorization: Bearer secret_...`.
- `PLATFORM_MCP_ECWID_STORE_ID` — Ecwid store id (shown in the admin footer / URL); every call goes to https://app.ecwid.com/api/v3/{store_id}/...

## Run

    uvx platform-mcp-hub serve ecwid          # Python
    npx -y platform-mcp-hub serve ecwid       # TypeScript
    claude mcp add ecwid -- uvx platform-mcp-hub serve ecwid

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/ecwid-mcp`. Python and TypeScript serve identical tools.
