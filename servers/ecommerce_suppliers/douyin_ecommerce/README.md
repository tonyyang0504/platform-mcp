# Douyin E-commerce — 抖店 (Doudian) seller + 精选联盟 / 巨量百应 + Doudian Open Platform MCP server

Category: **ecommerce_suppliers** · Docs: https://op.jinritemai.com/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_suppliers/douyin_ecommerce.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /product/listV2` (https://op.jinritemai.com/docs/api-docs/14/633)
- `list_products` — `GET /product/listV2` (https://op.jinritemai.com/docs/api-docs/14/633)
- `get_product` — `GET /product/detail` (https://op.jinritemai.com/docs/api-docs/14/56)
- `get_order` — `GET /order/orderDetail` (https://op.jinritemai.com/docs/api-docs/15/1343)
- `track` — `GET /order/orderDetail` (https://op.jinritemai.com/docs/api-docs/15/1343)
- ~~`quote_shipping`~~ not offered: The Doudian Open Platform is the seller-side API of your own shop (https://op.jinritemai.com/docs/guide-docs/10/23): freight is configured in freight templates, there is no shipping-quote call for a product and destination.
- ~~`create_order`~~ not offered: Orders are placed by buyers on Douyin; the seller API only reads and fulfils them (order.searchList, order.orderDetail, order.logisticsAdd — https://op.jinritemai.com/docs/api-docs/15/1342), so a supplier order cannot be created.

## Credentials

- `PLATFORM_MCP_DOUYIN_ECOMMERCE_APP_KEY` — Your Doudian app's app_key (抖店开放平台 → 应用管理).
- `PLATFORM_MCP_DOUYIN_ECOMMERCE_APP_SECRET` — The app's app_secret; it signs every call (hmac-sha256).
- `PLATFORM_MCP_DOUYIN_ECOMMERCE_ACCESS_TOKEN` — Shop access_token from /token/create (self-built apps: grant_type authorization_self with your shop_id). It lasts about 7 days; renew it with /token/refresh and update this value — the server does not renew it.

## Run

    uvx platform-mcp-hub serve douyin_ecommerce          # Python
    npx -y platform-mcp-hub serve douyin_ecommerce       # TypeScript
    claude mcp add douyin_ecommerce -- uvx platform-mcp-hub serve douyin_ecommerce

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/douyin_ecommerce-mcp`. Python and TypeScript serve identical tools.
