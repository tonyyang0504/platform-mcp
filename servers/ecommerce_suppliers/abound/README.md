# Abound (acquired — now Carro) MCP server

Category: **ecommerce_suppliers** · Docs: https://developers.moderndropship.com/reference/introduction · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_suppliers/abound.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /auth/me` (https://developers.moderndropship.com/openapi/shared-api.json)
- `list_products` — `GET /buyer/products` (https://developers.moderndropship.com/openapi/buyer-api.json)
- `get_product` — `GET /buyer/products/{product_id}` (https://developers.moderndropship.com/openapi/buyer-api.json)
- `get_order` — `GET /buyer/orders/{order_id}` (https://developers.moderndropship.com/openapi/buyer-api.json)
- ~~`create_order`~~ not offered: POST /buyer/orders requires `buyerReference` ('A reference to an ID in your (the buyer's) system. The ID must be unique.') and `orderedDate`, items[{variantId, quantity, buyerReference}] and shippingMethods[{code, title, price{amount, currency}}]; the vocabulary carries no order reference and its `shipping_option` string cannot be shaped into that array, so the body cannot be built without inventing values.
- ~~`quote_shipping`~~ not offered: No rate-quote endpoint: GET /shipping/methods lists the company's own configured shipping methods (page/limit) and takes no product or destination.
- ~~`track`~~ not offered: No tracking-events endpoint; sellerOrders[].fulfillments[{carrier, trackingCode, trackingUrls}] are part of GET /buyer/orders/{order_id} (see get_order).

## Credentials

- `PLATFORM_MCP_ABOUND_API_KEY` — Modern Dropship (Carro) API key generated under Settings > Dropshipping > Integrations, sent raw as `Authorization: <key>` (securityScheme ApiKeyAuth, no Bearer prefix). A buyer (retailer) key reaches the Buyer + Shared endpoints used here.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve abound   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve abound
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve abound   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/abound-mcp`. Python and TypeScript serve identical tools.
