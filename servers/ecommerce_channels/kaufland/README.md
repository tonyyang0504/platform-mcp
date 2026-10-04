# Kaufland Global Marketplace MCP server

Category: **ecommerce_channels** · Docs: https://sellerapi.kaufland.com/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_channels/kaufland.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /info/storefront` (https://sellerapi.kaufland.com/?page=endpoints)
- `set_inventory` — `PATCH /units/{listing_id}` (https://sellerapi.kaufland.com/?page=endpoints#/Units/patchUnit)
- `end_listing` — `DELETE /units/{listing_id}` (https://sellerapi.kaufland.com/?page=endpoints#/Units/deleteUnit)
- `list_orders` — `GET /order-units` (https://sellerapi.kaufland.com/?page=endpoints#/Order%20Units/GetOrderUnits)
- `mark_shipped` — `PATCH /order-units/{order_id}/send` (https://sellerapi.kaufland.com/?page=endpoints#/Order%20Units/SendOrderUnit)
- ~~`create_listing`~~ not offered: POST /v2/units adds an offer to an EXISTING Kaufland product and requires ean or id_product, id_offer, handling_time and listing_price in integral cents; new product data goes through /product-data; the vocabulary has no EAN/product id or handling time.
- ~~`update_listing`~~ not offered: PATCH /v2/units/{id_unit} takes listing_price 'in integral cents of the storefront's currency' — the vocabulary's decimal price cannot be converted without arithmetic — and titles/descriptions are product data, not unit fields; stock changes are set_inventory.

## Credentials

- `PLATFORM_MCP_KAUFLAND_CLIENT_KEY` — Kaufland Marketplace Client Key (32 characters, seller portal API settings), sent as the Shop-Client-Key header.
- `PLATFORM_MCP_KAUFLAND_SECRET_KEY` — The Secret Key (64 characters): signs every request (hex HMAC-SHA256 over METHOD, full URI, body and Unix timestamp joined by newlines, sent as Shop-Signature with Shop-Timestamp). Never sent on the wire.
- `PLATFORM_MCP_KAUFLAND_STOREFRONT` — Kaufland storefront your offers live on: de, cz, sk, pl, at, fr, it, es or nl (GET /v2/info/storefront lists yours); sent as ?storefront= on unit and order-unit calls.

## Run

    uvx platform-mcp-hub serve kaufland          # Python
    npx -y platform-mcp-hub serve kaufland       # TypeScript
    claude mcp add kaufland -- uvx platform-mcp-hub serve kaufland

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/kaufland-mcp`. Python and TypeScript serve identical tools.
