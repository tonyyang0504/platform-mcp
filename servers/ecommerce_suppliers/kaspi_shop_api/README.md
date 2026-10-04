# Kaspi.kz Shop (merchant API) MCP server

Category: **ecommerce_suppliers** · Docs: https://guide.kaspi.kz/partner/ru/shop/api/general · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_suppliers/kaspi_shop_api.json`; edit the catalog, not this file.

## Tools

- `me` — `GET https://kaspi.kz/shop/api/products/import/schema` (https://guide.kaspi.kz/partner/ru/shop/api/goods)
- `get_order` — `GET /orders` (https://guide.kaspi.kz/partner/ru/shop/api/orders)
- ~~`list_products`~~ not offered: The goods API only uploads products (POST /products/import) and reads import results, categories and attributes; there is no call that lists the shop's catalogue.
- ~~`get_product`~~ not offered: No product read endpoint in the goods API (import schema, classification attributes/values, import status only).
- ~~`quote_shipping`~~ not offered: No shipping-rate endpoint; delivery costs appear on the order (deliveryCostForSeller).
- ~~`create_order`~~ not offered: Seller-side API: customers order on kaspi.kz; the API accepts, cancels and completes those orders but cannot place one.
- ~~`track`~~ not offered: No tracking-events endpoint; Kaspi Доставка waybills are generated through order state changes and the order carries only state/plannedDeliveryDate.

## Credentials

- `PLATFORM_MCP_KASPI_SHOP_API_TOKEN` — Kaspi.kz merchant authorisation token from the seller cabinet (Настройки > Токен API), sent as the X-Auth-Token header.

## Run

    uvx platform-mcp-hub serve kaspi_shop_api          # Python
    npx -y platform-mcp-hub serve kaspi_shop_api       # TypeScript
    claude mcp add kaspi_shop_api -- uvx platform-mcp-hub serve kaspi_shop_api

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/kaspi_shop_api-mcp`. Python and TypeScript serve identical tools.
