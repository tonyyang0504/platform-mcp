# Kaufland Global Marketplace (sales channel) + Marketplace Seller API MCP server

Category: **ecommerce_suppliers** · Docs: https://sellerapi.kaufland.com/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_suppliers/kaufland_marketplace.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /info/storefront` (https://sellerapi.kaufland.com/?page=endpoints)
- `list_products` — `GET /products/search` (https://sellerapi.kaufland.com/?page=endpoints)
- `get_product` — `GET /products/{id}` (https://sellerapi.kaufland.com/?page=endpoints)
- `get_order` — `GET /orders/{id}` (https://sellerapi.kaufland.com/?page=endpoints)
- ~~`create_order`~~ not offered: Seller-side API: customers buy on kaufland.de; the API sends, cancels and refunds order units but cannot place an order.
- ~~`quote_shipping`~~ not offered: No rate quote endpoint; shipping is configured per offer through shipping groups (GET /v2/shipping-groups).
- ~~`track`~~ not offered: No tracking-events endpoint; the seller supplies carrier and tracking numbers when marking an order unit as sent (PATCH /v2/order-units/{id}/send).

## Credentials

- `PLATFORM_MCP_KAUFLAND_MARKETPLACE_CLIENT_KEY` — Kaufland Marketplace Client Key (32 characters, seller portal API settings), sent as the Shop-Client-Key header.
- `PLATFORM_MCP_KAUFLAND_MARKETPLACE_SECRET_KEY` — The Secret Key (64 characters): signs every request (hex HMAC-SHA256 over METHOD, full URI, body and Unix timestamp joined by newlines, sent as Shop-Signature with Shop-Timestamp). Never sent on the wire.
- `PLATFORM_MCP_KAUFLAND_MARKETPLACE_STOREFRONT` — Kaufland storefront for product calls: de, cz, sk, pl, at, fr, it, es or nl (GET /v2/info/storefront lists yours).

## Run

    uvx platform-mcp-hub serve kaufland_marketplace          # Python
    npx -y platform-mcp-hub serve kaufland_marketplace       # TypeScript
    claude mcp add kaufland_marketplace -- uvx platform-mcp-hub serve kaufland_marketplace

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/kaufland_marketplace-mcp`. Python and TypeScript serve identical tools.
