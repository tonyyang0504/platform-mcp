# Depop MCP server

Category: **ecommerce_channels** · Docs: https://partnerapi.depop.com/api-docs/terms/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_channels/depop.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /api/v1/shop/` (https://partnerapi.depop.com/api-docs/#operation/getSellerDetails)
- `update_listing` — `PATCH /api/v1/products/by-sku/{listing_id}/` (https://partnerapi.depop.com/api-docs/#operation/patchProduct)
- `set_inventory` — `PATCH /api/v1/products/by-sku/{sku}/` (https://partnerapi.depop.com/api-docs/#operation/patchProduct)
- `end_listing` — `DELETE /api/v1/products/by-sku/{listing_id}/` (https://partnerapi.depop.com/api-docs/#operation/deleteProduct)
- `list_orders` — `GET /api/v1/orders/` (https://partnerapi.depop.com/api-docs/#operation/getAllOrders)
- ~~`create_listing`~~ not offered: PUT /api/v1/products/by-sku/{sku}/ requires address.country_code, department, product_type, condition, brand_name, attributes, pictures and price_currency besides price and quantity; the vocabulary has no department, product type, condition or brand.
- ~~`mark_shipped`~~ not offered: markOrderAsShipped is POST /api/v1/orders/{purchase_id}/parcels/{parcel_id}/mark-as-shipped/ — it needs the parcel_id of the order's line items, which is not a vocabulary input.

## Credentials

- `PLATFORM_MCP_DEPOP_API_KEY` — Depop Partner API key (issued by Depop to approved enterprise partners; API-key tokens carry every scope); sent as Authorization: Bearer.
- `PLATFORM_MCP_DEPOP_API_HOST` — partnerapi.depop.com (production) or partnerapi-staging.depop.com (staging).

## Run

    uvx platform-mcp-hub serve depop          # Python
    npx -y platform-mcp-hub serve depop       # TypeScript
    claude mcp add depop -- uvx platform-mcp-hub serve depop

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/depop-mcp`. Python and TypeScript serve identical tools.
