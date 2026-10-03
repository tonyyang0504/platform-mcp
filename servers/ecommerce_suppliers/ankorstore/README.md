# Ankorstore MCP server

Category: **ecommerce_suppliers** · Docs: https://www.ankorstore.com/landings/integrations-api · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_suppliers/ankorstore.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /api/v1/me/config` (https://ankorstore.github.io/api-docs/#tag/Ankorstore_Getting-Started)
- `list_products` — `GET /api/v1/products` (https://ankorstore.github.io/api-docs/#tag/Ankorstore_Catalog/operation/list-products--Ankorstore)
- `get_product` — `GET /api/v1/products/{id}` (https://ankorstore.github.io/api-docs/#tag/Ankorstore_Catalog/operation/get-product--Ankorstore)
- `get_order` — `GET /api/v1/orders/{id}` (https://ankorstore.github.io/api-docs/#tag/Ankorstore_Ordering/operation/get-internal-order--Ankorstore)
- `track` — `GET /api/v1/orders/{order_id}` (https://ankorstore.github.io/api-docs/#tag/Ankorstore_Ordering/operation/get-internal-order--Ankorstore)
- ~~`quote_shipping`~~ not offered: POST /api/v1/orders/{order}/shipping-quotes quotes a label for an existing retailer order from parcel dimensions; there is no product/country shipping estimate.
- ~~`create_order`~~ not offered: The brand API cannot buy: retailers place wholesale orders in the Ankorstore marketplace UI. (Order-pay orders and POST /api/testing/orders/create are brand-invoicing and sandbox tools, not purchases from a supplier.)

## Credentials

- `PLATFORM_MCP_ANKORSTORE_CLIENT_ID` — client_id of an application created under Account > Integrations (https://ankorstore.com/account/integrations) of an Ankorstore BRAND account; exchanged at POST https://www.ankorstore.com/oauth/token (grant_type=client_credentials, scope=*) for a 1-hour bearer token that is renewed automatically.
- `PLATFORM_MCP_ANKORSTORE_CLIENT_SECRET` — client_secret of that application (sent in the form body of the token request).

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve ankorstore   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve ankorstore
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve ankorstore   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/ankorstore-mcp`. Python and TypeScript serve identical tools.
