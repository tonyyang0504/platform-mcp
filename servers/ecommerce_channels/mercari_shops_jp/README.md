# Mercari Shops (JP) MCP server

Category: **ecommerce_channels** · Docs: https://api.mercari-shops.com/docs/index.html · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_channels/mercari_shops_jp.json`; edit the catalog, not this file.

## Tools

- `me` — `POST /v1/graphql` (https://api.mercari-shops.com/docs/index.html#query-shop)
- `update_listing` — `POST /v1/graphql` (https://api.mercari-shops.com/docs/index.html#mutation-updateProduct)
- `end_listing` — `POST /v1/graphql` (https://api.mercari-shops.com/docs/index.html#mutation-updateProduct)
- `set_inventory` — `POST /v1/graphql` (https://api.mercari-shops.com/docs/index.html#mutation-updateProductVariant)
- `list_orders` — `POST /v1/graphql` (https://api.mercari-shops.com/docs/index.html#query-orderTransactions)
- ~~`create_listing`~~ not offered: createProduct requires categoryId, condition, shippingMethod, shippingPayer, shippingDuration, shippingFromStateId and imageUrls plus variants; the vocabulary has no category, condition or shipping settings.
- ~~`mark_shipped`~~ not offered: Shipping is two mutations in the current API — createOrderShipping (products and quantities of the shipment) then completeOrderShipping — with the tracking code set by updateOrderShippingTrackingCode; the one-call completeOrder and updateShippingTrackingCode are deprecated ('Use createOrderShipping and completeOrderShipping instead').

## Credentials

- `PLATFORM_MCP_MERCARI_SHOPS_JP_ACCESS_TOKEN` — Personal API Access Token issued on your mercari Shops shop administration page; sent as Authorization: Bearer.
- `PLATFORM_MCP_MERCARI_SHOPS_JP_API_HOST` — api.mercari-shops.com (production) or api.mercari-shops-sandbox.com (sandbox).
- `PLATFORM_MCP_MERCARI_SHOPS_JP_USER_AGENT` — User-Agent required by mercari Shops: <API_CLIENT_NAME>/<VERSION>, where API_CLIENT_NAME is the value Mercari assigns to your company at contract (e.g. EXAMPLE_SHOP/1.0.0); requests without the correct User-Agent are restricted.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve mercari_shops_jp   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve mercari_shops_jp
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve mercari_shops_jp   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/mercari_shops_jp-mcp`. Python and TypeScript serve identical tools.
