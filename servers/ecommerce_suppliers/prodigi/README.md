# Prodigi MCP server

Category: **ecommerce_suppliers** · Docs: https://www.prodigi.com/print-api/docs/reference/ · Verified: None

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_suppliers/prodigi.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /Orders` (https://www.prodigi.com/print-api/docs/reference/#orders)
- `get_product` — `GET /products/{id}` (https://www.prodigi.com/print-api/docs/reference/#products)
- `create_order` — `POST /Orders` (https://www.prodigi.com/print-api/docs/reference/#orders)
- `get_order` — `GET /Orders/{id}` (https://www.prodigi.com/print-api/docs/reference/#orders)
- ~~`list_products`~~ not offered: No catalogue browse endpoint: products are SKUs chosen in the Prodigi dashboard; GET /v4.0/products/{sku} only reads one.
- ~~`quote_shipping`~~ not offered: POST /v4.0/quotes takes nested items[{sku, copies, attributes, assets[{printArea}]}] plus shippingMethod/destinationCountryCode/currencyCode; the runtime's flat body form cannot build the items array from product_id/quantity.
- ~~`track`~~ not offered: No tracking-events endpoint; shipments[{carrier{name, service}, tracking{number, url}}] are part of the order record (see get_order).

## Credentials

- `PLATFORM_MCP_PRODIGI_API_KEY` — Prodigi API key for the LIVE environment (dashboard), sent as `X-API-Key`. A Sandbox key needs PLATFORM_MCP_PRODIGI_ENV=sandbox (https://api.sandbox.prodigi.com/v4.0).
- `PLATFORM_MCP_PRODIGI_ENV` — Vendor environment (default production): sandbox = https://api.sandbox.prodigi.com/v4.0. Credentials are the environment's own; see adapter.environments in the catalog entry.
- `PLATFORM_MCP_PRODIGI_BASE_URL` — Optional https base URL override (a mock or a private gateway); replaces the selected environment's base_url. Never echoed in errors.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve prodigi   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve prodigi
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve prodigi   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/prodigi-mcp`. Python and TypeScript serve identical tools.
