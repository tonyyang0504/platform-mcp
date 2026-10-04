# Nova Engel (ES perfumery & cosmetics dropshipping) MCP server

Category: **ecommerce_suppliers** · Docs: https://www.novaengel.com/dropshipping_productos · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_suppliers/nova_engel.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /api/products/paging/{access_token}/1/1/{language}` (https://drop.novaengel.com/swagger/docs/v1)
- `list_products` — `GET /api/products/paging/{access_token}/{pages}/{elements}/{language}` (https://drop.novaengel.com/swagger/docs/v1)
- `create_order` — `POST /api/orders/sendv2/{access_token}` (https://drop.novaengel.com/swagger/docs/v1)
- `get_order` — `GET /api/orders/orderbyid/{access_token}/{id}` (https://drop.novaengel.com/swagger/docs/v1)
- `track` — `GET /api/orders/orderbyid/{access_token}/{order_id}` (https://drop.novaengel.com/swagger/docs/v1)
- ~~`get_product`~~ not offered: The Swagger (https://drop.novaengel.com/swagger/docs/v1) has no single-product call: products come only in lists (/api/products/paging, /availables, /offers, /brand/{id}) and /api/products/image/{token}/{id} returns just an image.
- ~~`quote_shipping`~~ not offered: No shipping-quote operation exists in the Swagger (https://drop.novaengel.com/swagger/docs/v1); orders are sent with /api/orders/sendv2 and charges appear afterwards on the OrderModel (Charge1, Charge2).

## Credentials

- `PLATFORM_MCP_NOVA_ENGEL_USER` — Your Nova Engel dropshipping web-service user (issued with the approved dropshipping account).
- `PLATFORM_MCP_NOVA_ENGEL_PASSWORD` — The password of that web-service user.
- `PLATFORM_MCP_NOVA_ENGEL_LANGUAGE` — Language code for product texts in the URL path, e.g. es, en, fr, it, pt or de (the {language} segment of /api/products/…).

## Run

    uvx platform-mcp-hub serve nova_engel          # Python
    npx -y platform-mcp-hub serve nova_engel       # TypeScript
    claude mcp add nova_engel -- uvx platform-mcp-hub serve nova_engel

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/nova_engel-mcp`. Python and TypeScript serve identical tools.
