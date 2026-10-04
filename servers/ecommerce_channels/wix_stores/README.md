# Wix Stores MCP server

Category: **ecommerce_channels** · Docs: https://dev.wix.com/docs/rest/business-solutions/stores/introduction · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_channels/wix_stores.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /site-properties/v4/properties` (https://dev.wix.com/docs/rest/business-management/site-properties/properties/get-site-properties)
- `list_orders` — `POST /ecom/v1/orders/search` (https://dev.wix.com/docs/rest/business-solutions/e-commerce/orders/orders/search-orders)
- ~~`create_listing`~~ not offered: POST /stores/v3/products needs product.variantsInfo.variants[{price{actualPrice{amount}}, sku}] (the price sits in an array of objects) plus physicalProperties for PHYSICAL products — not expressible in the flat/dotted body.
- ~~`update_listing`~~ not offered: PATCH /stores/v3/products/{id} requires the current `revision` (read-then-write; 409 otherwise) and variant prices live in the variantsInfo.variants array.
- ~~`end_listing`~~ not offered: Hiding a product is PATCH /stores/v3/products/{id} {product: {id, revision, visible: false}} — the current `revision` is required (read-then-write, 409 otherwise) and cannot be supplied by the body form; DELETE /stores/v3/products/{id} is irreversible.
- ~~`set_inventory`~~ not offered: PATCH /stores/v3/inventory-items/{id} requires inventoryItem.revision (read-then-write) and is addressed by inventory-item id, not product id or SKU.
- ~~`mark_shipped`~~ not offered: POST /ecom/v1/fulfillments/orders/{orderId}/create-fulfillment requires fulfillment.lineItems[{id, quantity}] (an array of the order's line-item GUIDs) beside trackingInfo{trackingNumber, shippingProvider} — not expressible in the flat/dotted body.
- ~~`listing_metrics`~~ not offered: No per-product analytics endpoint in the Stores / eCommerce REST APIs.

## Credentials

- `PLATFORM_MCP_WIX_STORES_API_KEY` — Account API key from the Wix API Key Manager (account owner; Wix Stores + eCommerce scopes, site access) sent raw in the Authorization header (no Bearer prefix).
- `PLATFORM_MCP_WIX_STORES_SITE_ID` — Site id of the store (API keys are account-level, so every site-level call must carry the wix-site-id header).

## Run

    uvx platform-mcp-hub serve wix_stores          # Python
    npx -y platform-mcp-hub serve wix_stores       # TypeScript
    claude mcp add wix_stores -- uvx platform-mcp-hub serve wix_stores

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/wix_stores-mcp`. Python and TypeScript serve identical tools.
