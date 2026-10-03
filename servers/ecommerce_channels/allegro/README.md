# Allegro MCP server

Category: **ecommerce_channels** · Docs: https://developer.allegro.pl/documentation · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_channels/allegro.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /me` (https://developer.allegro.pl/documentation#operation/meGET)
- `update_listing` — `PATCH /sale/product-offers/{listing_id}` (https://developer.allegro.pl/documentation#operation/editProductOffers)
- `end_listing` — `PUT /sale/offer-publication-commands/{command_id}` (https://developer.allegro.pl/documentation#operation/changePublicationStatusUsingPUT)
- `set_inventory` — `PATCH /sale/product-offers/{listing_id}` (https://developer.allegro.pl/documentation#operation/editProductOffers)
- `list_orders` — `GET /order/checkout-forms` (https://developer.allegro.pl/documentation#operation/getListOfOrdersUsingGET)
- `mark_shipped` — `POST /order/checkout-forms/{order_id}/shipments` (https://developer.allegro.pl/documentation#operation/createOrderShipmentsUsingPOST)
- ~~`create_listing`~~ not offered: POST /sale/product-offers needs productSet[{product: {id, idType: GTIN|PRODUCT_ID}}] (an Allegro catalogue product, or a new product with category.id and the category's required parameters[]) plus delivery {shippingRates.id}, afterSalesServices policies and stock; the vocabulary has no product identifier, category or policy ids, and creation may finish asynchronously (202 + operation polling).
- ~~`listing_metrics`~~ not offered: No per-offer visits or sales statistics call in the REST API reference (swagger.yaml has /sale/offer-events and classified-ad statistics only).

## Credentials

- `PLATFORM_MCP_ALLEGRO_CLIENT_ID` — Client ID of your app registered at apps.developer.allegro.pl; sent with the secret as HTTP Basic on the token call.
- `PLATFORM_MCP_ALLEGRO_CLIENT_SECRET` — Client Secret of the same app.
- `PLATFORM_MCP_ALLEGRO_REFRESH_TOKEN` — Refresh token from a one-time authorization-code (or device-flow) consent of the seller account (valid 3 months). It is SINGLE-USE: every refresh returns a new pair (access token 12 h + new refresh token) and the old refresh token stops working 60 seconds after its first use. The runtime keeps a rotated refresh token in memory; set PLATFORM_MCP_STATE_DIR to also save it (<dir>/<platform>.json, mode 0600) so it is preferred over this variable on the next start. Without the state directory, a restart after the first refresh needs a fresh refresh token.
- `PLATFORM_MCP_ALLEGRO_CURRENCY` — Currency of your offers' base marketplace, PLN for allegro.pl; used by update_listing for sellingMode.price {amount, currency}.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve ecommerce_channels/allegro   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve ecommerce_channels/allegro
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve ecommerce_channels/allegro   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/allegro-ecommerce-channels-mcp`. Python and TypeScript serve identical tools.
