# Blurb (RPI Print) MCP server

Category: **ecommerce_suppliers** · Docs: https://www.blurb.com/print-api-software · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_suppliers/blurb.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /orders` (https://docs.api.rpiprint.com/api-reference)
- `create_order` — `POST /orders/create` (https://docs.api.rpiprint.com/api-reference)
- `get_order` — `GET /orders/{customerOrderId}` (https://docs.api.rpiprint.com/api-reference)
- ~~`list_products`~~ not offered: No catalogue endpoint: products are SKUs documented on the Product specifications pages (https://docs.api.rpiprint.com/products-main), not served by the API.
- ~~`get_product`~~ not offered: No product endpoint (see list_products); POST /pricing/production prices a SKU + page count + quantity but needs an orderItems array.
- ~~`quote_shipping`~~ not offered: POST /orders/shipping/estimate takes the create-order body (destination{...} + orderItems[{sku, quantity, product}]); the vocabulary's product_id/country/quantity cannot be shaped into that body by the runtime's flat body form.
- ~~`track`~~ not offered: No tracking-events endpoint; shipmentTracking[{trackingNumber, shipMethod, shipDate, estimatedArrival}] are part of GET /orders/{customerOrderId} (see get_order).

## Credentials

- `PLATFORM_MCP_BLURB_API_KEY` — RPI Print (Blurb Self-Service) API Key from the Print API Dashboard > API Credentials; the HTTP Basic username.
- `PLATFORM_MCP_BLURB_SHARED_SECRET` — RPI Print Shared Secret from the same dashboard page; the HTTP Basic password.

## Run

    uvx platform-mcp-hub serve blurb          # Python
    npx -y platform-mcp-hub serve blurb       # TypeScript
    claude mcp add blurb -- uvx platform-mcp-hub serve blurb

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/blurb-mcp`. Python and TypeScript serve identical tools.
