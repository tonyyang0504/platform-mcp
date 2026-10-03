# Jumia MCP server

Category: **ecommerce_channels** · Docs: https://vendorcenter.jumia.com/api-docs/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_channels/jumia.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /shops` (https://vendorcenter.jumia.com/api-docs/#tag/Shops/operation/get-shops)
- `set_inventory` — `POST /feeds/products/stock` (https://vendorcenter.jumia.com/api-docs/#tag/Products/operation/post-feeds-products-stock)
- `list_orders` — `GET /orders` (https://vendorcenter.jumia.com/api-docs/#tag/Orders/operation/get-orders)
- ~~`create_listing`~~ not offered: Product creation goes through the /feeds/products/create feed with category, brand, attribute set and variation data; the vocabulary has no category or brand.
- ~~`update_listing`~~ not offered: The price feed POST /feeds/products/price requires id (product SID), sellerSku AND price for every product; update_listing has no SKU input, so the required sellerSku cannot be supplied.
- ~~`end_listing`~~ not offered: Status changes use the /feeds/products/status feed, which requires id, sellerSku and per-country businessClients[{businessClientCode, status}]; end_listing carries neither the SKU nor the business client.
- ~~`mark_shipped`~~ not offered: Shipping is item-based: POST /orders/pack and /orders/ready-to-ship take orderItemIds (and shipment provider / tracking per package), not an order id.

## Credentials

- `PLATFORM_MCP_JUMIA_CLIENT_ID` — Client Id of a SELF AUTHORIZATION application registered in Vendor Center > Settings > Applications (Web Applications cannot refresh unattended).
- `PLATFORM_MCP_JUMIA_REFRESH_TOKEN` — Refresh token from the application's 'Generate Token' action in Vendor Center. Every refresh returns a NEW refresh token; the runtime keeps it in memory and, with PLATFORM_MCP_STATE_DIR set, saves it to <dir>/jumia.json (0600) so a restart uses the latest one.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve jumia   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve jumia
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve jumia   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/jumia-mcp`. Python and TypeScript serve identical tools.
