# Shopee Brasil MCP server

Category: **ecommerce_channels** · Docs: https://open.shopee.com/developer-guide/4 · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_channels/shopee_br.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /api/v2/shop/get_shop_info` (https://open.shopee.com/documents/v2/v2.shop.get_shop_info?module=92&type=1)
- `list_orders` — `GET /api/v2/order/get_order_list` (https://open.shopee.com/documents/v2/v2.order.get_order_list?module=94&type=1)
- `mark_shipped` — `POST /api/v2/logistics/ship_order` (https://open.shopee.com/documents/v2/v2.logistics.ship_order?module=95&type=1)
- `set_inventory` — `POST /api/v2/product/update_stock` (https://open.shopee.com/documents/v2/v2.product.update_stock?module=89&type=1)
- `update_listing` — `POST /api/v2/product/update_price` (https://open.shopee.com/documents/v2/v2.product.update_price?module=89&type=1)
- `end_listing` — `POST /api/v2/product/unlist_item` (https://open.shopee.com/documents/v2/v2.product.unlist_item?module=89&type=1)
- ~~`create_listing`~~ not offered: v2.product.add_item (https://open.shopee.com/documents/v2/v2.product.add_item?module=89&type=1) requires category_id, image.image_id_list from v2.media_space.upload_image, logistic_info channel settings, weight and brand; the vocabulary's create_listing has none of these inputs.

## Credentials

- `PLATFORM_MCP_SHOPEE_BR_PARTNER_KEY` — partner_key (live key) of the app; signs the token refresh and every shop call (HMAC-SHA256). Never sent on the wire.
- `PLATFORM_MCP_SHOPEE_BR_REFRESH_TOKEN` — refresh_token from GetAccessToken (/api/v2/auth/token/get) after the shop authorised the app (https://open.shopee.com/developer-guide/20). Valid 30 days and rotated on every refresh; set PLATFORM_MCP_STATE_DIR so the newest one survives restarts.
- `PLATFORM_MCP_SHOPEE_BR_PARTNER_ID` — partner_id of your Shopee Open Platform app (Console > App).
- `PLATFORM_MCP_SHOPEE_BR_SHOP_ID` — shop_id of the authorised shop (returned in the authorisation redirect).

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve shopee_br   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve shopee_br
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve shopee_br   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/shopee_br-mcp`. Python and TypeScript serve identical tools.
