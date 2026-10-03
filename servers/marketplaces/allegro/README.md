# Allegro MCP server

Category: **marketplaces** · Docs: https://developer.allegro.pl · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/marketplaces/allegro.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /me` (https://developer.allegro.pl/documentation#operation/meGET)
- `list_products` — `GET /sale/offers` (https://developer.allegro.pl/documentation#operation/searchOffersUsingGET)
- `get_product` — `GET /sale/product-offers/{product_id}` (https://developer.allegro.pl/documentation#operation/getProductOffer)
- `update_price` — `PATCH /sale/product-offers/{product_id}` (https://developer.allegro.pl/documentation#operation/editProductOffers)
- `list_sales` — `GET /order/checkout-forms` (https://developer.allegro.pl/documentation#operation/getListOfOrdersUsingGET)
- `list_refunds` — `GET /payments/refunds` (https://developer.allegro.pl/documentation#operation/getRefundedPayments)
- ~~`create_product`~~ not offered: POST /sale/product-offers needs productSet[{product: {id, idType}}] (an Allegro catalogue product or a new product with category.id and required parameters), delivery shipping rates and after-sales policies (https://developer.allegro.pl/documentation#operation/createProductOffers); the vocabulary carries none of these ids.
- ~~`get_sales_stats`~~ not offered: The REST API has no revenue summary endpoint; sales exist only as individual checkout forms (https://developer.allegro.pl/documentation#operation/getListOfOrdersUsingGET).
- ~~`refund`~~ not offered: POST /payments/refunds requires payment.id, a reason and per-line-item quantities or values (lineItems[] with the checkout form's line item ids) (https://developer.allegro.pl/documentation#operation/initiateRefund); a sale id and a single amount cannot express it.

## Credentials

- `PLATFORM_MCP_ALLEGRO_CLIENT_ID` — Client ID of your app registered at apps.developer.allegro.pl; sent with the secret as HTTP Basic on the token call.
- `PLATFORM_MCP_ALLEGRO_CLIENT_SECRET` — Client Secret of the same app.
- `PLATFORM_MCP_ALLEGRO_REFRESH_TOKEN` — Refresh token from a one-time authorization-code (or device-flow) consent of the seller account (valid 3 months). It is SINGLE-USE: every refresh returns a new pair (access token 12 h + new refresh token) and the old refresh token stops working 60 seconds after its first use. The runtime keeps a rotated refresh token in memory; set PLATFORM_MCP_STATE_DIR to also save it (<dir>/<platform>.json, mode 0600) so it is preferred over this variable on the next start. Without the state directory, a restart after the first refresh needs a fresh refresh token. The state file is keyed by platform id, so it is shared with ecommerce_channels/allegro: give each server its own PLATFORM_MCP_STATE_DIR (or its own consent / refresh token) so the two never race on one single-use refresh token.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve marketplaces/allegro   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve marketplaces/allegro
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve marketplaces/allegro   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/allegro-marketplaces-mcp`. Python and TypeScript serve identical tools.
