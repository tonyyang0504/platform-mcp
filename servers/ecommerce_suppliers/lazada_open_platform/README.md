# Lazada Seller Center + Lazada Open Platform MCP server

Category: **ecommerce_suppliers** · Docs: https://open.lazada.com/apps/doc/api · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_suppliers/lazada_open_platform.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /rest/seller/get` (https://open.lazada.com/apps/doc/api?path=%2Fseller%2Fget)
- `list_products` — `GET /rest/products/get` (https://open.lazada.com/apps/doc/api?path=%2Fproducts%2Fget)
- `get_product` — `GET /rest/product/item/get` (https://open.lazada.com/apps/doc/api?path=%2Fproduct%2Fitem%2Fget)
- `get_order` — `GET /rest/order/get` (https://open.lazada.com/apps/doc/api?path=%2Forder%2Fget)
- `track` — `GET /rest/logistic/order/trace` (https://open.lazada.com/apps/doc/api?path=%2Flogistic%2Forder%2Ftrace)
- ~~`quote_shipping`~~ not offered: The Lazada Open Platform APIs (https://open.lazada.com/apps/doc/api) are seller-side (Seller, Product, Order, Logistics …); there is no buyer-side freight quote for sourcing.
- ~~`create_order`~~ not offered: Orders are placed by shoppers; the Order API group (GetOrder, GetOrders, GetOrderItems, SetInvoiceNumber …, https://open.lazada.com/apps/doc/api?path=%2Forder%2Fget) has no order creation.

## Credentials

- `PLATFORM_MCP_LAZADA_OPEN_PLATFORM_APP_KEY` — App Key of your Lazada Open Platform app (App Console).
- `PLATFORM_MCP_LAZADA_OPEN_PLATFORM_APP_SECRET` — App Secret of the same app; signs every call: uppercase hex HMAC-SHA256 over the API name (e.g. /order/get) + the parameters sorted by name as name+value. Never sent on the wire.
- `PLATFORM_MCP_LAZADA_OPEN_PLATFORM_ACCESS_TOKEN` — Seller access_token from the seller-authorisation code exchange (/auth/token/create). It expires (see expires_in); renew it with the signed system API /auth/token/refresh and update this value — the runtime does not refresh it.
- `PLATFORM_MCP_LAZADA_OPEN_PLATFORM_DOMAIN` — Country gateway of the seller's shop: sg, com.my, co.th, co.id, com.ph or vn → https://api.lazada.{domain}/rest (Service Endpoints on every API page).

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve lazada_open_platform   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve lazada_open_platform
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve lazada_open_platform   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/lazada_open_platform-mcp`. Python and TypeScript serve identical tools.
