# Amazon MCP server

Category: **ecommerce_channels** · Docs: https://developer-docs.amazon.com/sp-api · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_channels/amazon.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /sellers/v1/marketplaceParticipations` (https://developer-docs.amazon.com/sp-api/reference/getmarketplaceparticipations)
- `update_listing` — `PATCH /listings/2021-08-01/items/{seller_id}/{listing_id}` (https://developer-docs.amazon.com/sp-api/reference/patchlistingsitem)
- `end_listing` — `DELETE /listings/2021-08-01/items/{seller_id}/{listing_id}` (https://developer-docs.amazon.com/sp-api/reference/deletelistingsitem)
- `set_inventory` — `PATCH /listings/2021-08-01/items/{seller_id}/{sku}` (https://developer-docs.amazon.com/sp-api/reference/patchlistingsitem)
- `list_orders` — `GET /orders/v0/orders` (https://developer-docs.amazon.com/sp-api/reference/getorders)
- ~~`create_listing`~~ not offered: putListingsItem (PUT /listings/2021-08-01/items/{sellerId}/{sku}) requires {productType, requirements, attributes{...}} where attributes are product-type-specific arrays defined by the Product Type Definitions API (item_name[{value, language_tag, marketplace_id}], condition_type, purchasable_offer, externally_assigned_product_identifier, ...); the vocabulary has no product type and the attribute schema changes per type.
- ~~`mark_shipped`~~ not offered: confirmShipment (POST /orders/v0/orders/{orderId}/shipmentConfirmation) requires {marketplaceId, packageDetail{packageReferenceId, carrierCode, trackingNumber, shipDate, orderItems[{orderItemId, quantity}]}} — the orderItemIds come from getOrderItems (GET /orders/v0/orders/{orderId}/orderItems) first, two calls.
- ~~`listing_metrics`~~ not offered: Per-listing sales and traffic are only available through asynchronous Reports (createReport, poll getReport, download the document) or Data Kiosk queries — no synchronous metrics call.

## Credentials

- `PLATFORM_MCP_AMAZON_CLIENT_ID` — LWA client identifier of your SP-API application (Developer Central / Solution Provider Portal > app > LWA credentials).
- `PLATFORM_MCP_AMAZON_CLIENT_SECRET` — LWA client secret of the same application.
- `PLATFORM_MCP_AMAZON_REFRESH_TOKEN` — LWA refresh token (Atzr|...) from self-authorising the app for your seller account (or from the seller's OAuth authorization); exchanged at https://api.amazon.com/auth/o2/token for 1-hour access tokens sent as x-amz-access-token.
- `PLATFORM_MCP_AMAZON_REGION` — SP-API endpoint region: na (Canada, US, Mexico, Brazil), eu (Europe, UK, India, Middle East, Turkey, South Africa) or fe (Japan, Australia, Singapore); calls go to https://sellingpartnerapi-<region>.amazon.com.
- `PLATFORM_MCP_AMAZON_SELLER_ID` — Selling partner (merchant token) id used in the Listings Items path /listings/2021-08-01/items/{sellerId}/{sku} (Seller Central > Settings > Account Info > Merchant Token).
- `PLATFORM_MCP_AMAZON_MARKETPLACE_ID` — Marketplace id the tools act on, e.g. ATVPDKIKX0DER (US) or A1F83G8C2ARO7P (UK); see the SP-API Marketplace IDs page.
- `PLATFORM_MCP_AMAZON_CURRENCY` — Currency of the marketplace's offers (e.g. USD, GBP, EUR); needed only when update_listing changes the price (purchasable_offer selector).
- `PLATFORM_MCP_AMAZON_ENV` — Vendor environment (default production): sandbox = https://sandbox.sellingpartnerapi-{region}.amazon.com. Credentials are the environment's own; see adapter.environments in the catalog entry.
- `PLATFORM_MCP_AMAZON_BASE_URL` — Optional https base URL override (a mock or a private gateway); replaces the selected environment's base_url. Never echoed in errors.

## Run

    uvx platform-mcp-hub serve amazon          # Python
    npx -y platform-mcp-hub serve amazon       # TypeScript
    claude mcp add amazon -- uvx platform-mcp-hub serve amazon

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/amazon-mcp`. Python and TypeScript serve identical tools.
