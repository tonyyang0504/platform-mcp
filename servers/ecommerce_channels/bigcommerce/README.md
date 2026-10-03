# BigCommerce MCP server

Category: **ecommerce_channels** · Docs: https://docs.bigcommerce.com/docs/start/authentication/api-accounts · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_channels/bigcommerce.json`; edit the catalog, not this file.

## Tools

- `me` — `GET https://api.bigcommerce.com/stores/{store_hash}/v2/store` (https://docs.bigcommerce.com/developer/api-reference/rest/admin/management/store-information/v2/get-store-information)
- `create_listing` — `POST https://api.bigcommerce.com/stores/{store_hash}/v3/catalog/products` (https://docs.bigcommerce.com/developer/api-reference/rest/admin/catalog/products/create-product)
- `update_listing` — `PUT https://api.bigcommerce.com/stores/{store_hash}/v3/catalog/products/{listing_id}` (https://docs.bigcommerce.com/developer/api-reference/rest/admin/catalog/products/update-product)
- `end_listing` — `PUT https://api.bigcommerce.com/stores/{store_hash}/v3/catalog/products/{listing_id}` (https://docs.bigcommerce.com/developer/api-reference/rest/admin/catalog/products/update-product)
- `set_inventory` — `PUT https://api.bigcommerce.com/stores/{store_hash}/v3/catalog/products/{listing_id}` (https://docs.bigcommerce.com/developer/api-reference/rest/admin/catalog/products/update-product)
- `list_orders` — `GET https://api.bigcommerce.com/stores/{store_hash}/v2/orders` (https://docs.bigcommerce.com/developer/api-reference/rest/admin/management/orders/get-orders)
- `mark_shipped` — `PUT https://api.bigcommerce.com/stores/{store_hash}/v2/orders/{order_id}` (https://docs.bigcommerce.com/developer/api-reference/rest/admin/management/orders/update-order)
- ~~`listing_metrics`~~ not offered: No per-product analytics endpoint in the Catalog or Orders APIs (product `view_count`/`total_sold` are read-only fields on the product record, not a metrics call; store analytics are in the control panel only).

## Credentials

- `PLATFORM_MCP_BIGCOMMERCE_ACCESS_TOKEN` — Store-level API account access token (Settings > Store-level API accounts; scopes Products modify, Orders modify) sent as the X-Auth-Token header.
- `PLATFORM_MCP_BIGCOMMERCE_STORE_HASH` — Permanent store hash from the API path (https://api.bigcommerce.com/stores/{store_hash}/...), shown with the API account.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve bigcommerce   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve bigcommerce
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve bigcommerce   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/bigcommerce-mcp`. Python and TypeScript serve identical tools.
