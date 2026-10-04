# eBay MCP server

Category: **ecommerce_channels** · Docs: https://developer.ebay.com/develop/apis/restful-apis/sell-apis · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_channels/ebay.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /sell/account/v1/privilege` (https://developer.ebay.com/api-docs/sell/account/resources/privilege/methods/getPrivileges)
- `update_listing` — `POST /sell/inventory/v1/bulk_update_price_quantity` (https://developer.ebay.com/api-docs/sell/inventory/resources/inventory_item/methods/bulkUpdatePriceQuantity)
- `end_listing` — `POST /sell/inventory/v1/offer/{listing_id}/withdraw` (https://developer.ebay.com/api-docs/sell/inventory/resources/offer/methods/withdrawOffer)
- `set_inventory` — `POST /sell/inventory/v1/bulk_update_price_quantity` (https://developer.ebay.com/api-docs/sell/inventory/resources/inventory_item/methods/bulkUpdatePriceQuantity)
- `list_orders` — `GET /sell/fulfillment/v1/order` (https://developer.ebay.com/api-docs/sell/fulfillment/resources/order/methods/getOrders)
- ~~`create_listing`~~ not offered: Needs a three-call chain: PUT /sell/inventory/v1/inventory_item/{sku} {product{title, description, imageUrls[]}, condition, availability{shipToLocationAvailability{quantity}}} (Content-Language header), then POST /sell/inventory/v1/offer {sku, marketplaceId, format: FIXED_PRICE, pricingSummary{price{value, currency}}, listingPolicies{fulfillmentPolicyId, paymentPolicyId, returnPolicyId}, merchantLocationKey, categoryId} returning offerId, then POST /sell/inventory/v1/offer/{offerId}/publish — the runtime maps one verb to one call.
- ~~`mark_shipped`~~ not offered: POST /sell/fulfillment/v1/order/{orderId}/shipping_fulfillment requires lineItems[{lineItemId, quantity}] (the order's own line-item ids, read with GET /sell/fulfillment/v1/order/{orderId} first) besides shippingCarrierCode and trackingNumber — two calls.
- ~~`listing_metrics`~~ not offered: Sell Analytics getTrafficReport (GET /sell/analytics/v1/traffic_report, scope sell.analytics.readonly; page not re-read this pass) takes dimension=LISTING and a composed filter string (marketplace_ids:{EBAY_US},date_range:[yyyymmdd..yyyymmdd],listing_ids:{id}) that the adapter expressions cannot assemble.

## Credentials

- `PLATFORM_MCP_EBAY_CLIENT_ID` — Production keyset App ID (Client ID) from developer.ebay.com > Application Keys; sent with the Cert ID as HTTP Basic on the token call.
- `PLATFORM_MCP_EBAY_CLIENT_SECRET` — Production keyset Cert ID (Client Secret).
- `PLATFORM_MCP_EBAY_REFRESH_TOKEN` — User refresh token (v^1.1#...) from a one-time authorization-code consent that granted at least sell.inventory, sell.fulfillment and sell.account (the refresh request re-asks exactly these scopes, which must be a subset of the consent); long-lived (about 18 months), revoked when the seller changes password. 2-hour user access tokens are minted from it.
- `PLATFORM_MCP_EBAY_CURRENCY` — Currency of your listings' marketplace (e.g. USD, GBP, EUR); needed only by update_listing, since eBay prices are {value, currency} objects.
- `PLATFORM_MCP_EBAY_ENV` — Vendor environment (default production): sandbox = https://api.sandbox.ebay.com. Credentials are the environment's own; see adapter.environments in the catalog entry.
- `PLATFORM_MCP_EBAY_BASE_URL` — Optional https base URL override (a mock or a private gateway); replaces the selected environment's base_url. Never echoed in errors.

## Run

    uvx platform-mcp-hub serve ebay          # Python
    npx -y platform-mcp-hub serve ebay       # TypeScript
    claude mcp add ebay -- uvx platform-mcp-hub serve ebay

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/ebay-mcp`. Python and TypeScript serve identical tools.
