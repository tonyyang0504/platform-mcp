# Lemon Squeezy MCP server

Category: **marketplaces** · Docs: https://docs.lemonsqueezy.com/api · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/marketplaces/lemon_squeezy.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /users/me` (https://docs.lemonsqueezy.com/api/users/retrieve-user)
- `list_products` — `GET /products` (https://docs.lemonsqueezy.com/api/products/list-all-products)
- `get_product` — `GET /products/{product_id}` (https://docs.lemonsqueezy.com/api/products/retrieve-product)
- `list_sales` — `GET /orders` (https://docs.lemonsqueezy.com/api/orders/list-all-orders)
- `get_sales_stats` — `GET /stores/{store_id}` (https://docs.lemonsqueezy.com/api/stores/the-store-object)
- `refund` — `POST /orders/{sale_id}/refund` (https://docs.lemonsqueezy.com/api/orders/issue-refund)
- ~~`create_product`~~ not offered: Products are created in the dashboard; the API reference lists only The product object, Retrieve a product and List all products (https://docs.lemonsqueezy.com/api/products/the-product-object).
- ~~`update_price`~~ not offered: Prices live on variants / price objects, which the API exposes read-only (Retrieve / List only: https://docs.lemonsqueezy.com/api/variants/the-variant-object, https://docs.lemonsqueezy.com/api/prices/the-price-object).
- ~~`list_refunds`~~ not offered: There is no refunds resource; refunds are the refunded / refunded_amount / refunded_at attributes and status refunded or partial_refund on orders (https://docs.lemonsqueezy.com/api/orders/the-order-object) - use list_sales.

## Credentials

- `PLATFORM_MCP_LEMON_SQUEEZY_API_KEY` — Lemon Squeezy API key (Settings > API > create key; 'Generated API keys are valid for a year'), sent as 'Authorization: Bearer {api_key}'. Test-mode keys only see test-mode data (https://docs.lemonsqueezy.com/api/getting-started/requests).
- `PLATFORM_MCP_LEMON_SQUEEZY_STORE_ID` — Numeric store id (GET /v1/stores). Filters list_products / list_sales with filter[store_id] and is required by get_sales_stats.
- `PLATFORM_MCP_LEMON_SQUEEZY_ENV` — Vendor environment (default production): sandbox = production host with test accounts or test keys. Credentials are the environment's own; see adapter.environments in the catalog entry.
- `PLATFORM_MCP_LEMON_SQUEEZY_BASE_URL` — Optional https base URL override (a mock or a private gateway); replaces the selected environment's base_url. Never echoed in errors.

## Run

    uvx platform-mcp-hub serve lemon_squeezy          # Python
    npx -y platform-mcp-hub serve lemon_squeezy       # TypeScript
    claude mcp add lemon_squeezy -- uvx platform-mcp-hub serve lemon_squeezy

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/lemon_squeezy-mcp`. Python and TypeScript serve identical tools.
