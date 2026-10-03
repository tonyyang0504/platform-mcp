# Walmart Marketplace MCP server

Category: **ecommerce_channels** · Docs: https://developer.walmart.com/doc/us/mp/us-mp-getting-started/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_channels/walmart.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /v3/token/detail` (https://developer.walmart.com/us-marketplace/reference/gettokendetail)
- `list_orders` — `GET /v3/orders` (https://developer.walmart.com/us-marketplace/reference/getallorders)
- `update_listing` — `PUT /v3/price` (https://developer.walmart.com/us-marketplace/reference/updateprice)
- `set_inventory` — `PUT /v3/inventory` (https://developer.walmart.com/us-marketplace/reference/updateinventoryforanitem)
- `end_listing` — `DELETE /v3/items/{listing_id}` (https://developer.walmart.com/us-marketplace/reference/retireanitem)
- ~~`create_listing`~~ not offered: New items are created only through the asynchronous item feed (POST /v3/feeds?feedType=MP_ITEM with the category's item spec: productIdentifiers, brand, category attributes, shipping weight — https://developer.walmart.com/us-marketplace/docs/item-management-api-overview); the vocabulary carries none of the required spec fields.
- ~~`mark_shipped`~~ not offered: Shipping updates (POST /v3/orders/{purchaseOrderId}/shipping, https://developer.walmart.com/us-marketplace/reference/shippingupdates) are per ORDER LINE: each orderLine needs its lineNumber, statusQuantity and trackingInfo (shipDateTime, carrierName.carrier, methodCode); line numbers are not a vocabulary input.

## Credentials

- `PLATFORM_MCP_WALMART_CLIENT_ID` — Walmart Marketplace API Client ID (Seller Center > Settings > API Key Management / Developer Portal, production keys).
- `PLATFORM_MCP_WALMART_CLIENT_SECRET` — The matching Client Secret; sent only as HTTP Basic to POST /v3/token, which returns a 15-minute access token sent as WM_SEC.ACCESS_TOKEN.
- `PLATFORM_MCP_WALMART_SHIP_NODE` — shipNode id for set_inventory when you have several ship nodes; empty = your default ship node.
- `PLATFORM_MCP_WALMART_ENV` — Vendor environment (default production): sandbox = https://sandbox.walmartapis.com; sandbox_dynamic = https://sandbox.walmartapis.com. Credentials are the environment's own; see adapter.environments in the catalog entry.
- `PLATFORM_MCP_WALMART_BASE_URL` — Optional https base URL override (a mock or a private gateway); replaces the selected environment's base_url. Never echoed in errors.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve walmart   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve walmart
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve walmart   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/walmart-mcp`. Python and TypeScript serve identical tools.
