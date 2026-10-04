# theprintspace / creativehub MCP server

Category: **ecommerce_suppliers** · Docs: https://sell.creativehub.io/api-docs · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_suppliers/theprintspace.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /drops` (https://sell.creativehub.io/api-docs#list-drops)
- `list_products` — `GET /products` (https://sell.creativehub.io/api-docs#list-products)
- `get_product` — `GET /products/{id}` (https://sell.creativehub.io/api-docs#get-product)
- `quote_shipping` — `POST /orders/quote` (https://sell.creativehub.io/api-docs#quote-order)
- `create_order` — `POST /orders` (https://sell.creativehub.io/api-docs#create-order)
- `get_order` — `GET /orders/{id}` (https://sell.creativehub.io/api-docs#list-orders)
- ~~`track`~~ not offered: Not documented: 'Each API token can carry a webhook_uri ... intended for order-status events. Not yet active ... until then poll your store platform for order state, or GET /v1/orders/{order_id}' (get_order); no tracking endpoint exists.

## Credentials

- `PLATFORM_MCP_THEPRINTSPACE_API_TOKEN` — creativehub API token (Settings > API access at https://sell.creativehub.io/settings; API access must be enabled on the account, otherwise 403). Shown once at creation; sent as Authorization: Bearer <token>.

## Run

    uvx platform-mcp-hub serve theprintspace          # Python
    npx -y platform-mcp-hub serve theprintspace       # TypeScript
    claude mcp add theprintspace -- uvx platform-mcp-hub serve theprintspace

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/theprintspace-mcp`. Python and TypeScript serve identical tools.
