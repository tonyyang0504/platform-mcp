# SPOD / Spreadconnect (Spreadshirt) MCP server

Category: **ecommerce_suppliers** · Docs: https://api.spreadconnect.app/docs/ · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_suppliers/spreadconnect.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /authentication` (https://api.spreadconnect.app/docs/#operation/authentication%20info)
- `list_products` — `GET /articles` (https://api.spreadconnect.app/docs/#operation/getArticles)
- `get_product` — `GET /articles/{articleId}` (https://api.spreadconnect.app/docs/#operation/getArticle)
- `get_order` — `GET /orders/{orderId}` (https://api.spreadconnect.app/docs/#operation/getOrder)
- `track` — `GET /orders/{orderId}/shipments` (https://api.spreadconnect.app/docs/#operation/getShipments)
- ~~`create_order`~~ not offered: POST /orders requires `phone` ('Must not be blank'), `email` ('Must be a valid email address'), `externalOrderReference` ('external order reference from merchant (you). Must not be blank') and shipping{address, customerPrice{amount, currency}} beside orderItems[{sku, quantity, customerPrice}]; the vocabulary carries no customer price, phone or merchant reference, so the body cannot be built without inventing values.
- ~~`quote_shipping`~~ not offered: GET /orders/{orderId}/shippingTypes lists shipping types with prices for an existing order only; there is no quote for a product_id/country/quantity before an order exists.

## Credentials

- `PLATFORM_MCP_SPREADCONNECT_ACCESS_TOKEN` — Spreadconnect API token (create an API Integration in the Spreadconnect web app; the token is on its dashboard), sent as the `X-SPOD-ACCESS-TOKEN` header.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve spreadconnect   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve spreadconnect
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve spreadconnect   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/spreadconnect-mcp`. Python and TypeScript serve identical tools.
