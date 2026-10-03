# Shopee Seller Centre + Shopee Open Platform MCP server

Category: **ecommerce_suppliers** · Docs: https://open.shopee.com/documents · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_suppliers/shopee_open_platform.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /api/v2/shop/get_shop_info` (https://open.shopee.com/documents/v2/v2.shop.get_shop_info?module=89&type=1)
- `list_products` — `GET /api/v2/product/get_item_list` (https://open.shopee.com/documents/v2/v2.product.get_item_list?module=89&type=1)
- `get_product` — `GET /api/v2/product/get_item_base_info` (https://open.shopee.com/documents/v2/v2.product.get_item_base_info?module=89&type=1)
- `get_order` — `GET /api/v2/order/get_order_detail` (https://open.shopee.com/documents/v2/v2.order.get_order_detail?module=89&type=1)
- `track` — `GET /api/v2/logistics/get_tracking_info` (https://open.shopee.com/documents/v2/v2.logistics.get_tracking_info?module=89&type=1)
- ~~`quote_shipping`~~ not offered: Shopee is a sales channel: shipping fees are charged to buyers at checkout; the logistics APIs (e.g. https://open.shopee.com/documents/v2/v2.logistics.get_tracking_info?module=89&type=1) fulfil existing orders and do not quote shipping for a product and country.
- ~~`create_order`~~ not offered: Orders are placed by Shopee buyers; the Order module (https://open.shopee.com/documents/v2/v2.order.get_order_detail?module=89&type=1) reads and ships them and has no create call.

## Credentials

- `PLATFORM_MCP_SHOPEE_OPEN_PLATFORM_PARTNER_ID` — partner_id of your Shopee Open Platform app (Console > App list).
- `PLATFORM_MCP_SHOPEE_OPEN_PLATFORM_PARTNER_KEY` — The app's partner_key; signs the refresh request and every call (lower-case hex HMAC-SHA256) and is never sent.
- `PLATFORM_MCP_SHOPEE_OPEN_PLATFORM_SHOP_ID` — shop_id that authorised the app (returned in the authorisation redirect).
- `PLATFORM_MCP_SHOPEE_OPEN_PLATFORM_REFRESH_TOKEN` — The shop's refresh_token from v2.public.get_access_token (valid 30 days, single-use). Each refresh (every ~4 h) returns a new one that replaces it (persisted when PLATFORM_MCP_STATE_DIR is set).
- `PLATFORM_MCP_SHOPEE_OPEN_PLATFORM_HOST` — API host: partner.shopeemobile.com (global production), openplatform.shopee.cn (mainland China), openplatform.shopee.com.br (Brazil) or openplatform.sandbox.test-stable.shopee.sg (sandbox).

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve shopee_open_platform   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve shopee_open_platform
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve shopee_open_platform   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/shopee_open_platform-mcp`. Python and TypeScript serve identical tools.
