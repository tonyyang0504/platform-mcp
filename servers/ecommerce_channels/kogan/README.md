# Kogan Marketplace MCP server

Category: **ecommerce_channels** · Docs: https://developers.kogan.com/docs · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_channels/kogan.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /products/` (https://nimda.kogan.com/api/marketplace/v2/#operation/products_get)
- `update_listing` — `PATCH /products/` (https://nimda.kogan.com/api/marketplace/v2/#operation/products_update)
- `set_inventory` — `POST /products/stockprice/` (https://nimda.kogan.com/api/marketplace/v2/#operation/products_stock_price_update)
- `end_listing` — `POST /products/status/` (https://nimda.kogan.com/api/marketplace/v2/#operation/products_enabled_update)
- `list_orders` — `GET /orders/` (https://nimda.kogan.com/api/marketplace/v2/#operation/orders_list)
- ~~`create_listing`~~ not offered: POST /products/ requires product_sku, title, description, brand, category, product_gtin, images, product_condition and per-currency offer_data {price, handling_days}; the vocabulary has no category, brand, GTIN or handling time.
- ~~`mark_shipped`~~ not offered: POST /orders/fulfill/ takes dispatch lines per order ITEM: [{ID, Items: [{OrderItemID, SellerSku, Quantity, ShippedDateUtc, TrackingNumber, ShippingCarrier}]}]; item ids, SKUs and quantities are not vocabulary inputs.

## Credentials

- `PLATFORM_MCP_KOGAN_SELLER_TOKEN` — SellerToken (API key) issued by your Kogan Marketplace account manager after the marketplace application is approved (UAT and production keys differ); sent as the SellerToken header.
- `PLATFORM_MCP_KOGAN_SELLER_ID` — SellerID (your Kogan marketplace account name) issued with the token; sent as the SellerID header.
- `PLATFORM_MCP_KOGAN_API_HOST` — nimda.kogan.com for production, or nimda-marketplace.aws.kgn.io for the UAT test environment; calls go to https://<api_host>/api/marketplace/v2/...

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve kogan   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve kogan
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve kogan   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/kogan-mcp`. Python and TypeScript serve identical tools.
