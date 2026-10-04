# Faire MCP server

Category: **ecommerce_channels** · Docs: https://developers.faire.com/docs · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_channels/faire.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /brands/profile` (https://developers.faire.com/docs#/paths/brands-profile/get)
- `update_listing` — `PATCH /products/{listing_id}` (https://developers.faire.com/docs#/paths/products-product_id/patch)
- `end_listing` — `DELETE /products/{listing_id}` (https://developers.faire.com/docs#/paths/products-product_id/delete)
- `set_inventory` — `PATCH /product-inventory/by-skus` (https://developers.faire.com/docs#/paths/product-inventory-by-skus/patch)
- `list_orders` — `GET /orders` (https://developers.faire.com/docs#/paths/orders/get)
- `mark_shipped` — `POST /orders/{order_id}/shipments` (https://developers.faire.com/docs#/paths/orders-order_id--shipments/post)
- ~~`create_listing`~~ not offered: POST /products needs a taxonomy_type, variants with per-region prices (wholesale and retail), unit_multiplier and minimum_order_quantity to publish ('saved as a draft with publicationWarnings when it does not' meet Faire's publication requirements, https://developers.faire.com/docs#/paths/products/post); the vocabulary has one price and no category.

## Credentials

- `PLATFORM_MCP_FAIRE_ACCESS_TOKEN` — Faire OAuth access token for the brand (Authorization Code Grant: POST https://www.faire.com/api/external-api-oauth2/token), sent as X-FAIRE-OAUTH-ACCESS-TOKEN. Scopes: READ_BRAND, READ_PRODUCTS, WRITE_PRODUCTS, READ_ORDERS, WRITE_ORDERS, WRITE_INVENTORIES.
- `PLATFORM_MCP_FAIRE_APP_CREDENTIALS` — Base64 of applicationId:applicationSecret from the Faire Developer Portal, sent as X-FAIRE-APP-CREDENTIALS (required together with the OAuth access token).

## Run

    uvx platform-mcp-hub serve faire          # Python
    npx -y platform-mcp-hub serve faire       # TypeScript
    claude mcp add faire -- uvx platform-mcp-hub serve faire

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/faire-mcp`. Python and TypeScript serve identical tools.
