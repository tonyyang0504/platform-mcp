# Flipkart MCP server

Category: **ecommerce_channels** · Docs: https://seller.flipkart.com/api-docs/FMSAPI.html · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_channels/flipkart.json`; edit the catalog, not this file.

## Tools

- `me` — `POST /v3/shipments/filter/` (https://seller.flipkart.com/api-docs/order-api-docs/OMAPIRef.html)
- `list_orders` — `POST /v3/shipments/filter/` (https://seller.flipkart.com/api-docs/order-api-docs/OMAPIRef.html)
- ~~`create_listing`~~ not offered: POST /listings/v3 takes a body keyed by the SKU itself ({"<sku>": {product_id, price, tax, listing_status, shipping_fees, fulfillment_profile, packages, locations}}); object keys built from an argument cannot be expressed, and the vocabulary lacks product_id, HSN/tax and package data.
- ~~`update_listing`~~ not offered: POST /listings/v3/update/price uses the same SKU-keyed body ({"<sku>": {product_id, price: {mrp, selling_price, currency}}}), i.e. an object key taken from the argument, which the declarative body cannot build.
- ~~`set_inventory`~~ not offered: POST /listings/v3/update/inventory is keyed by SKU ({"<sku>": {product_id, locations: [{id, inventory}]}}) and needs the Flipkart product_id and location id; not expressible with fixed body keys.
- ~~`end_listing`~~ not offered: Listing status changes go through POST /listings/v3/update with the same SKU-keyed body (listing_status INACTIVE); not expressible with fixed body keys.
- ~~`mark_shipped`~~ not offered: The dispatch calls in the Order Management API reference (POST /v3/shipments/dispatch, POST /v3/shipments/selfShip/dispatch, preceded by /v3/shipments/labels) operate on shipmentIds and the seller's dispatch location rather than an order id plus tracking number; those ids are not vocabulary inputs.

## Credentials

- `PLATFORM_MCP_FLIPKART_ACCESS_TOKEN` — Seller API access token of your Self Access Application (Seller Dashboard > Manage Profile > Developer Access): obtain it with GET https://api.flipkart.net/oauth-service/oauth/token?grant_type=client_credentials&scope=Seller_Api,Default using HTTP Basic appId:appSecret. It is valid about 60 days; replace it when calls start failing with 401 (the runtime cannot run Flipkart's GET token call itself).

## Run

    uvx platform-mcp-hub serve flipkart          # Python
    npx -y platform-mcp-hub serve flipkart       # TypeScript
    claude mcp add flipkart -- uvx platform-mcp-hub serve flipkart

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/flipkart-mcp`. Python and TypeScript serve identical tools.
