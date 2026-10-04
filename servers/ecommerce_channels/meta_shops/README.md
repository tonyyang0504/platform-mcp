# Facebook & Instagram Shops MCP server

Category: **ecommerce_channels** · Docs: https://developers.facebook.com/docs/commerce-platform/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_channels/meta_shops.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /{cid}` (https://developers.facebook.com/docs/marketing-api/reference/product-catalog/)
- `update_listing` — `POST /{cid}/items_batch` (https://developers.facebook.com/docs/marketing-api/catalog-batch/reference)
- `set_inventory` — `POST /{cid}/items_batch` (https://developers.facebook.com/docs/marketing-api/catalog-batch/reference)
- `end_listing` — `POST /{cid}/items_batch` (https://developers.facebook.com/docs/marketing-api/catalog-batch/reference)
- `list_orders` — `GET /{cms}/commerce_orders` (https://developers.facebook.com/docs/commerce-platform/order-management/order-api)
- `mark_shipped` — `POST /{order_id}/shipments` (https://developers.facebook.com/docs/commerce-platform/order-management/fulfillment-api)
- ~~`create_listing`~~ not offered: A PRODUCT_ITEM CREATE needs link, image_link, brand, condition and availability besides id/title/description/price; the vocabulary has no product page link, brand or condition.

## Credentials

- `PLATFORM_MCP_META_SHOPS_ACCESS_TOKEN` — System-user (or long-lived user) access token of a Meta app with catalog_management and, for orders, commerce_account_manage_orders / commerce_account_read_orders permissions on the commerce account; sent as Authorization: Bearer.
- `PLATFORM_MCP_META_SHOPS_CATALOG_ID` — Product catalog id (Commerce Manager > Catalog > Settings).
- `PLATFORM_MCP_META_SHOPS_CMS_ID` — Commerce account (CMS) id; required for list_orders.
- `PLATFORM_MCP_META_SHOPS_CURRENCY` — ISO currency of the catalog prices, e.g. USD; required when update_listing sends a price ('9.99 USD').

## Run

    uvx platform-mcp-hub serve meta_shops          # Python
    npx -y platform-mcp-hub serve meta_shops       # TypeScript
    claude mcp add meta_shops -- uvx platform-mcp-hub serve meta_shops

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/meta_shops-mcp`. Python and TypeScript serve identical tools.
