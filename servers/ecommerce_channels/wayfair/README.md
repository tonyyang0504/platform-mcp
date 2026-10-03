# Wayfair (supplier) MCP server

Category: **ecommerce_channels** · Docs: https://developer.wayfair.io/posts/introduction · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_channels/wayfair.json`; edit the catalog, not this file.

## Tools

- `me` — `POST /graphql` (https://developer.wayfair.io/posts/dropship-orders-asn)
- `list_orders` — `POST /graphql` (https://developer.wayfair.io/posts/dropship-orders-asn)
- `set_inventory` — `POST /graphql` (https://developer.wayfair.io/posts/dropship-inventory)
- `end_listing` — `POST /graphql` (https://developer.wayfair.io/posts/dropship-inventory)
- ~~`create_listing`~~ not offered: Product Addition is an asynchronous orchestrated workflow: discover taxonomyCategoryId and its attribute questions, a manufacturerId from brandAssociations and a marketContext, then submit and poll submissions (https://developer.wayfair.io/posts/catalog-product-addition); the vocabulary has no category, brand or attributes.
- ~~`update_listing`~~ not offered: Product Update is asynchronous and split by level: updateMarketSpecificCatalogItems needs a marketContext (country, brand, language, locale) and item-group updates the SKU itemGroupId, with results polled through statusOfUpdateRequest (https://developer.wayfair.io/posts/catalog-product-update); prices are not part of it.
- ~~`mark_shipped`~~ not offered: The shipment (ASN) mutation requires supplierId, packageCount, carrierCode (SCAC), shipSpeed, shipDate, sourceAddress and per-package items {partNumber, quantity} matching the PO (https://developer.wayfair.io/posts/dropship-orders-asn); the vocabulary only carries order_id, carrier and tracking_number.

## Credentials

- `PLATFORM_MCP_WAYFAIR_CLIENT_ID` — Production Client ID of your application (Wayfair Developer Portal > Application Management; needs the 'API' role in Partner Home and a completed sandbox test).
- `PLATFORM_MCP_WAYFAIR_CLIENT_SECRET` — Production Client Secret of the same application; exchanged at https://sso.auth.wayfair.com/oauth/token for a 24-hour bearer token.
- `PLATFORM_MCP_WAYFAIR_SUPPLIER_ID` — Numeric Wayfair supplier ID used in inventory feeds: your warehouse ID for a child-level feed, or the supplier account ID for a parent-level feed (Partner Home > Warehouse Management).

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve wayfair   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve wayfair
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve wayfair   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/wayfair-mcp`. Python and TypeScript serve identical tools.
