# Paddle MCP server

Category: **marketplaces** · Docs: https://developer.paddle.com · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/marketplaces/paddle.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /event-types` (https://developer.paddle.com/api-reference/event-types/list-event-types)
- `list_products` — `GET /products` (https://developer.paddle.com/api-reference/products/list-products)
- `get_product` — `GET /products/{product_id}` (https://developer.paddle.com/api-reference/products/get-product)
- `create_product` — `POST /products` (https://developer.paddle.com/api-reference/products/create-product)
- `update_price` — `POST /prices` (https://developer.paddle.com/api-reference/prices/create-price)
- `list_sales` — `GET /transactions` (https://developer.paddle.com/api-reference/transactions/list-transactions)
- `list_refunds` — `GET /adjustments` (https://developer.paddle.com/api-reference/adjustments/list-adjustments)
- `refund` — `POST /adjustments` (https://developer.paddle.com/api-reference/adjustments/create-adjustment)
- ~~`get_sales_stats`~~ not offered: No revenue-totals endpoint: the Reports API (POST /reports, then GET /reports/{report_id}/download-url) produces an asynchronous CSV report of transactions or adjustments rather than a totals object the runtime could map.

## Credentials

- `PLATFORM_MCP_PADDLE_API_KEY` — Paddle API key (Paddle > Developer tools > Authentication; live keys look like pdl_live_apikey_...) sent as Authorization: Bearer. Give it product.read, product.write, price.write, transaction.read, adjustment.read and adjustment.write permissions for the full tool set. Sandbox keys (pdl_sdbx_apikey_...) need base https://sandbox-api.paddle.com, which this server does not switch to.
- `PLATFORM_MCP_PADDLE_TAX_CATEGORY` — Tax category for create_product (POST /products requires it): standard, digital-goods, ebooks, implementation-services, professional-services, saas, software-programming-services, training-services or website-hosting. Only create_product needs it.
- `PLATFORM_MCP_PADDLE_ENV` — Vendor environment (default production): sandbox = https://sandbox-api.paddle.com. Credentials are the environment's own; see adapter.environments in the catalog entry.
- `PLATFORM_MCP_PADDLE_BASE_URL` — Optional https base URL override (a mock or a private gateway); replaces the selected environment's base_url. Never echoed in errors.

## Run

    uvx platform-mcp-hub serve paddle          # Python
    npx -y platform-mcp-hub serve paddle       # TypeScript
    claude mcp add paddle -- uvx platform-mcp-hub serve paddle

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/paddle-mcp`. Python and TypeScript serve identical tools.
