# StockX MCP server

Category: **ecommerce_channels** · Docs: https://developer.stockx.com/portal/getting-started/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_channels/stockx.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /selling/listings` (https://developer.stockx.com/portal/api-reference#tag/Listings/operation/GetAllListings)
- `update_listing` — `PATCH /selling/listings/{listing_id}` (https://developer.stockx.com/portal/api-reference#tag/Listings/operation/Update)
- `end_listing` — `PUT /selling/listings/{listing_id}/deactivate` (https://developer.stockx.com/portal/api-reference#tag/Listings/operation/DeactivateListing)
- `list_orders` — `GET /selling/orders/active` (https://developer.stockx.com/portal/api-reference#tag/Order/operation/GetOrders)
- ~~`create_listing`~~ not offered: POST /selling/listings requires a StockX catalogue variantId (UUID) plus amount ('required': ['amount', 'variantId'], https://developer.stockx.com/portal/api-reference#tag/Listings/operation/Create); the vocabulary's title/sku cannot identify a variant.
- ~~`set_inventory`~~ not offered: A StockX listing is a single ask for one unit of a variant; there is no quantity or stock field on CreateListingInput/UpdateListingInput (https://developer.stockx.com/portal/api-reference#tag/Listings).
- ~~`mark_shipped`~~ not offered: Sellers ship with StockX-generated shipping documents (GET /selling/orders/{orderNumber}/shipping-document); the API has no call to submit a carrier or tracking number (https://developer.stockx.com/portal/api-reference#tag/Order).

## Credentials

- `PLATFORM_MCP_STOCKX_API_KEY` — StockX API key from the Developer Portal Keys page (issued after developer access approval), sent as x-api-key on every call.
- `PLATFORM_MCP_STOCKX_CLIENT_ID` — Client ID of your StockX application (Developer Portal > Applications; one application per StockX account).
- `PLATFORM_MCP_STOCKX_CLIENT_SECRET` — Client Secret of the same application.
- `PLATFORM_MCP_STOCKX_REFRESH_TOKEN` — Refresh token from a one-time Authorization Code consent (https://accounts.stockx.com/authorize with scope 'offline_access openid' and audience gateway.stockx.com, then POST /oauth/token grant_type=authorization_code). The runtime exchanges it for 12-hour access tokens (grant_type=refresh_token, audience=gateway.stockx.com).
- `PLATFORM_MCP_STOCKX_CURRENCY` — Currency code of your asks (AUD, CAD, CHF, EUR, GBP, HKD, JPY, KRW, MXN, NZD, SGD, USD); StockX defaults to USD when omitted.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve stockx   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve stockx
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve stockx   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/stockx-mcp`. Python and TypeScript serve identical tools.
