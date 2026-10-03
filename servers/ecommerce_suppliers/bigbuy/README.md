# BigBuy MCP server

Category: **ecommerce_suppliers** · Docs: https://api.bigbuy.eu/rest/doc · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_suppliers/bigbuy.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /rest/user/auth/status.json` (https://api.bigbuy.eu/rest/doc)
- `list_products` — `GET /rest/catalog/productsinformation.json` (https://api.bigbuy.eu/rest/doc)
- `get_product` — `GET /rest/catalog/productinformation/{id}.json` (https://api.bigbuy.eu/rest/doc)
- `create_order` — `POST /rest/order/create.json` (https://api.bigbuy.eu/rest/doc)
- `get_order` — `GET /rest/order/{orderId}.json` (https://api.bigbuy.eu/rest/doc)
- `track` — `GET /rest/tracking/order/{idOrder}.json` (https://api.bigbuy.eu/rest/doc)
- ~~`quote_shipping`~~ not offered: POST /rest/shipping/orders.json takes nested order{products[{reference, quantity}], delivery{isoCountry, postCode}} and POST /rest/shipping/lowest-shipping-cost-by-country.json answers a single {reference, cost, carrierId, carrierName} object rather than an options list; neither fits the vocabulary's product_id/country/quantity -> options[] shape.

## Credentials

- `PLATFORM_MCP_BIGBUY_API_KEY` — BigBuy API key from the control panel (API access is part of BigBuy's paid packs), sent as `Authorization: Bearer` (JWT bearer scheme in the OpenAPI spec). Sandbox keys need base https://api.sandbox.bigbuy.eu, which this server does not switch to.
- `PLATFORM_MCP_BIGBUY_ISO_CODE` — Two-letter language for product texts and tracking descriptions (the `isoCode` query parameter, e.g. en); BigBuy defaults to es when unset.
- `PLATFORM_MCP_BIGBUY_PAYMENT_METHOD` — paymentMethod for create_order: paypal, moneybox (prepaid purse, see GET /rest/user/purse) or bankwire; left out of the body when unset.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve bigbuy   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve bigbuy
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve bigbuy   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/bigbuy-mcp`. Python and TypeScript serve identical tools.
