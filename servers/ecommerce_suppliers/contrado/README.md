# Contrado MCP server

Category: **ecommerce_suppliers** · Docs: https://api.contrado.app/helix/docs/ · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_suppliers/contrado.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /helix/v1/stores` (https://api.contrado.app/helix/docs/)
- `list_products` — `GET /helix/v1/stores/products` (https://api.contrado.app/helix/docs/)
- `get_product` — `GET /helix/v1/stores/products/{storeProductId}` (https://api.contrado.app/helix/docs/)
- `get_order` — `GET /helix/v1/orders/{orderId}` (https://api.contrado.app/helix/docs/)
- ~~`create_order`~~ not offered: POST /helix/v1/orders/create takes StoreOrderRequestModel {externalReferenceId, recipient, lineItem[{storeProductId, variantId, selectedOptions, quantity, price}], totalAmount, currencyCode, cultureCode} and rejects 'Invalid quantity or pricing format'; the vocabulary carries no order total or currency, so the body cannot be built without inventing values.
- ~~`quote_shipping`~~ not offered: GET /helix/v1/shipping/{cultureCode} returns the store's shipping price groups and regional rates per culture code, not a quote for a product_id/country/quantity.
- ~~`track`~~ not offered: GET /helix/v1/orders/{orderId}/shipment/status answers a single object {courierName, shippingService, trackingId, shipmentStatus, deliveryEstimateDate, trackingUrl}, not a list of events; the tracking id and URL are part of get_order.

## Credentials

- `PLATFORM_MCP_CONTRADO_API_KEY` — Contrado Helix private token (Contrado Store Account > API Integration; shown once at creation), sent as `X-API-Key`. Scopes: StoresRead, StoreProductsRead, StoreOrdersRead.
- `PLATFORM_MCP_CONTRADO_STORE_ID` — Store id sent as `X-Store-Id`; needed only with an account-level token (a store-level token already names its store).

## Run

    uvx platform-mcp-hub serve contrado          # Python
    npx -y platform-mcp-hub serve contrado       # TypeScript
    claude mcp add contrado -- uvx platform-mcp-hub serve contrado

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/contrado-mcp`. Python and TypeScript serve identical tools.
