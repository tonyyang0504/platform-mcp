# Printful MCP server

Category: **ecommerce_suppliers** · Docs: https://developers.printful.com/docs/ · Verified: None

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_suppliers/printful.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /oauth/scopes` (https://developers.printful.com/docs/#tag/OAuth-API)
- `list_products` — `GET /products` (https://developers.printful.com/docs/#tag/Catalog-API)
- `get_product` — `GET /products/{id}` (https://developers.printful.com/docs/#tag/Catalog-API)
- `create_order` — `POST /orders` (https://developers.printful.com/docs/#tag/Orders-API/operation/createOrder)
- `get_order` — `GET /orders/{id}` (https://developers.printful.com/docs/#tag/Orders-API)
- ~~`quote_shipping`~~ not offered: POST /shipping/rates takes nested recipient{address1, city, country_code, state_code, zip} + items[{variant_id, quantity}]; the vocabulary's product_id/country/quantity cannot be shaped into that body by the runtime's flat body form.
- ~~`track`~~ not offered: No tracking-events endpoint; shipments[{tracking_number, tracking_url, carrier, service}] are part of GET /orders/{id} (see get_order).

## Credentials

- `PLATFORM_MCP_PRINTFUL_TOKEN` — Printful private (store-level) token or OAuth access token, sent as `Authorization: Bearer`. Account-level tokens also need the X-PF-Store-Id header, which the runtime cannot send: use a store token.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve printful   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve printful
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve printful   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/printful-mcp`. Python and TypeScript serve identical tools.
