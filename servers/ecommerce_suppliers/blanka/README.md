# Blanka MCP server

Category: **ecommerce_suppliers** · Docs: https://documenter.getpostman.com/view/10905449/2sA35LWzqV · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_suppliers/blanka.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /products/` (https://documenter.getpostman.com/view/10905449/2sA35LWzqV#get-products)
- `list_products` — `GET /products/` (https://documenter.getpostman.com/view/10905449/2sA35LWzqV#get-products)
- `create_order` — `POST /orders/` (https://documenter.getpostman.com/view/10905449/2sA35LWzqV#create-order)
- ~~`get_product`~~ not offered: The reference (Blanka API (Beta)) documents only Get Products (the paged list), Create Order and a webhook; there is no single-product endpoint.
- ~~`quote_shipping`~~ not offered: No shipping-rate endpoint in the reference; only Get Products, Create Order and the order-status webhook are documented.
- ~~`get_order`~~ not offered: No order-read endpoint: 'Webhook - update order status ... This webhook will fire when an order is shipped. Please provide us with a webhook endpoint to send the POST to.' ({order_id, tracking_code, status: SHIPPED}).
- ~~`track`~~ not offered: Tracking arrives only through the shipping webhook ({order_id, tracking_code, status: SHIPPED}) POSTed to an endpoint you give Blanka; there is no tracking call.

## Credentials

- `PLATFORM_MCP_BLANKA_API_KEY` — Blanka API key (VIP membership; request it from the merchant success team, hello@blankabrand.com). Blanka's Postman reference sends it as the Authorization header value, exactly as issued.

## Run

    uvx platform-mcp-hub serve blanka          # Python
    npx -y platform-mcp-hub serve blanka       # TypeScript
    claude mcp add blanka -- uvx platform-mcp-hub serve blanka

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/blanka-mcp`. Python and TypeScript serve identical tools.
