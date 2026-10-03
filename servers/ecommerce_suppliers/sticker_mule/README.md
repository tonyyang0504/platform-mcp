# Sticker Mule API MCP server

Category: **ecommerce_suppliers** · Docs: https://www.stickermule.com/api · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_suppliers/sticker_mule.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /items` (https://www.stickermule.com/api)
- `list_products` — `GET /items` (https://www.stickermule.com/api)
- `create_order` — `POST /orders` (https://www.stickermule.com/api)
- ~~`get_product`~~ not offered: No single-item endpoint; the documented endpoints are GET /api/items, /api/addresses, /api/payments, /api/orders and POST /api/orders only.
- ~~`quote_shipping`~~ not offered: No shipping-quote endpoint is documented.
- ~~`get_order`~~ not offered: GET /api/orders only lists placed orders ('most recent first', limit/offset) with no order-number filter; there is no single-order endpoint.
- ~~`track`~~ not offered: No tracking endpoint; GET /api/orders carries only shipmentState, expectedDeliveryDate and deliveredAt per order, no tracking numbers or events.

## Credentials

- `PLATFORM_MCP_STICKER_MULE_API_KEY` — Personal API key generated under Account settings > Store settings on stickermule.com (shown once; personal accounts only, not team accounts), sent as `Authorization: Bearer`. It can place orders on the saved payment methods.
- `PLATFORM_MCP_STICKER_MULE_PAYMENT_ID` — paymentId for create_order: a saved payment method id from GET /api/payments (not mapped). Orders are charged to it.
- `PLATFORM_MCP_STICKER_MULE_CURRENCY` — ISO 4217 currency for list_products prices (the `currency` query parameter; Sticker Mule defaults to USD).
- `PLATFORM_MCP_STICKER_MULE_LOCALE` — Locale for product names and prices in list_products (the `locale` query parameter; default en).

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve sticker_mule   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve sticker_mule
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve sticker_mule   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/sticker_mule-mcp`. Python and TypeScript serve identical tools.
