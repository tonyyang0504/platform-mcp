# Whop MCP server

Category: **marketplaces** · Docs: https://docs.whop.com · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/marketplaces/whop.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /accounts/me` (https://docs.whop.com/api-reference/beta/accounts/retrieve-account)
- `list_products` — `GET /products` (https://docs.whop.com/api-reference/products/list-products)
- `get_product` — `GET /products/{product_id}` (https://docs.whop.com/api-reference/products/retrieve-product)
- `create_product` — `POST /products` (https://docs.whop.com/api-reference/products/create-product)
- `update_price` — `POST /plans` (https://docs.whop.com/api-reference/beta/plans/create-plan)
- `list_sales` — `GET /payments` (https://docs.whop.com/api-reference/payments/list-payments)
- `list_refunds` — `GET /refunds` (https://docs.whop.com/api-reference/refunds/list-refunds)
- `refund` — `POST /payments/{sale_id}/refund` (https://docs.whop.com/api-reference/payments/refund-payment)
- ~~`get_sales_stats`~~ not offered: No revenue-totals endpoint in the Whop API: payments, refunds and invoices are listed individually (GET /payments, /refunds, /invoices) and analytics live in the dashboard.

## Credentials

- `PLATFORM_MCP_WHOP_API_KEY` — Whop Account API key (dashboard > Developer > API keys; server-side only) sent as Authorization: Bearer. Permissions used: access_pass:basic:read/manage (products), plan:basic:read/manage (update_price), payment:basic:read (sales, refunds) and payment:manage (refund). Sandbox keys use https://sandbox-api.whop.com/api/v1, which this server does not switch to.
- `PLATFORM_MCP_WHOP_COMPANY_ID` — The company's account id (biz_..., shown in the dashboard URL/settings). Sent as account_id on list_products, create_product, update_price, list_sales and list_refunds; without it GET /products would search the public marketplace.

## Run

    uvx platform-mcp-hub serve whop          # Python
    npx -y platform-mcp-hub serve whop       # TypeScript
    claude mcp add whop -- uvx platform-mcp-hub serve whop

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/whop-mcp`. Python and TypeScript serve identical tools.
