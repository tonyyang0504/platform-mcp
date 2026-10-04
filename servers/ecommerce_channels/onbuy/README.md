# OnBuy MCP server

Category: **ecommerce_channels** · Docs: https://docs.api.onbuy.com/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_channels/onbuy.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /v2/sites/{site}` (https://docs.api.onbuy.com/#sites-view)
- `update_listing` — `PUT /v2/listings/by-sku` (https://docs.api.onbuy.com/#product-listings-update-by-sku)
- `set_inventory` — `PUT /v2/listings/by-sku` (https://docs.api.onbuy.com/#product-listings-update-by-sku)
- `end_listing` — `DELETE /v2/listings/by-sku` (https://docs.api.onbuy.com/#product-listings-delete-by-sku)
- `list_orders` — `GET /v2/orders` (https://docs.api.onbuy.com/#orders-browse)
- `mark_shipped` — `PUT /v2/orders/dispatch` (https://docs.api.onbuy.com/#orders-dispatch)
- ~~`create_listing`~~ not offered: Listings are created on an existing OnBuy product: POST /v2/products/{opc}/listings needs the product's OPC code (or a product must first be created with category, brand and technical details via POST /v2/products); the vocabulary has no OPC or category.

## Credentials

- `PLATFORM_MCP_ONBUY_CONSUMER_KEY` — Consumer key from the OnBuy/OnCommerce Seller Control Panel > Integrations > OnBuy API (Test and Live keys differ).
- `PLATFORM_MCP_ONBUY_SECRET_KEY` — Secret key from the same page; exchanged with the consumer key at POST /v2/auth/request-token for a 15-minute access token (bound to the calling IP), sent as the raw Authorization header.
- `PLATFORM_MCP_ONBUY_SITE_ID` — OnBuy site id your listings/orders belong to: 2000 = OnBuy UK (GET /v2/sites lists the others).

## Run

    uvx platform-mcp-hub serve onbuy          # Python
    npx -y platform-mcp-hub serve onbuy       # TypeScript
    claude mcp add onbuy -- uvx platform-mcp-hub serve onbuy

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/onbuy-mcp`. Python and TypeScript serve identical tools.
