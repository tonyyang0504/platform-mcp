# Gelato MCP server

Category: **ecommerce_suppliers** · Docs: https://dashboard.gelato.com/docs/ · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_suppliers/gelato.json`; edit the catalog, not this file.

## Tools

- `me` — `GET https://product.gelatoapis.com/v3/catalogs` (https://dashboard.gelato.com/docs/products/catalog/list/)
- `list_products` — `POST https://product.gelatoapis.com/v3/catalogs/{catalogUid}/products:search` (https://dashboard.gelato.com/docs/products/product/search/)
- `get_product` — `GET https://product.gelatoapis.com/v3/products/{productUid}` (https://dashboard.gelato.com/docs/products/product/get/)
- `get_order` — `GET /v4/orders/{orderId}` (https://dashboard.gelato.com/docs/orders/v4/get/)
- ~~`create_order`~~ not offered: POST /v4/orders requires `orderReferenceId` ('Reference to your internal order id.') and `customerReferenceId` ('Reference to your internal customer id.') plus `currency` and items[{itemReferenceId, productUid, files[{type, url}], quantity}]; the vocabulary carries none of these references, so the body cannot be built without inventing values.
- ~~`quote_shipping`~~ not offered: POST /v4/orders:quote takes nested products[{itemReferenceId, productUid, files, quantity}] + recipient{country, ...}; the vocabulary's product_id/country/quantity cannot be shaped into that body by the runtime's flat body form.
- ~~`track`~~ not offered: No tracking-events endpoint; shipment.packages[{trackingCode, trackingUrl}] are part of GET /v4/orders/{orderId} (see get_order).

## Credentials

- `PLATFORM_MCP_GELATO_API_KEY` — Gelato API key (dashboard > Developer > API keys), sent as `X-API-KEY`. Product endpoints live on product.gelatoapis.com and are called by absolute URL.

## Run

    uvx platform-mcp-hub serve gelato          # Python
    npx -y platform-mcp-hub serve gelato       # TypeScript
    claude mcp add gelato -- uvx platform-mcp-hub serve gelato

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/gelato-mcp`. Python and TypeScript serve identical tools.
