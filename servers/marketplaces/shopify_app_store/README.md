# Shopify App Store MCP server

Category: **marketplaces** · Docs: https://shopify.dev/docs/apps/launch · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/marketplaces/shopify_app_store.json`; edit the catalog, not this file.

## Tools

- `me` — `POST /graphql.json` (https://shopify.dev/docs/api/partner/latest/queries/publicApiVersions)
- `get_product` — `POST /graphql.json` (https://shopify.dev/docs/api/partner/latest/queries/app)
- `list_sales` — `POST /graphql.json` (https://shopify.dev/docs/api/partner/latest/queries/transactions)
- `list_refunds` — `POST /graphql.json` (https://shopify.dev/docs/api/partner/latest/objects/AppSaleAdjustment)
- ~~`list_products`~~ not offered: The Partner API QueryRoot has an app(id) lookup but no query that lists an organization's apps (https://shopify.dev/docs/api/partner/latest).
- ~~`create_product`~~ not offered: Apps are created and submitted for App Store review in the Partner Dashboard; the Partner API reference has no app-creation operation (https://shopify.dev/docs/api/partner/latest).
- ~~`update_price`~~ not offered: App pricing plans are edited in the Partner Dashboard; the Partner API reference documents no pricing write (https://shopify.dev/docs/api/partner/latest).
- ~~`get_sales_stats`~~ not offered: The Partner API returns individual transactions only; no earnings summary query exists (https://shopify.dev/docs/api/partner/latest/queries/transactions).
- ~~`refund`~~ not offered: No refund operation for app charges is documented in the Partner API reference (https://shopify.dev/docs/api/partner/latest); refunds are issued from the Partner Dashboard.

## Credentials

- `PLATFORM_MCP_SHOPIFY_APP_STORE_ACCESS_TOKEN` — Partner API client access token (Partner Dashboard > Settings > Partner API clients, with the View financials permission for transactions and Manage apps for app data); 'The API client access token must belong to the organization that you're querying'. Sent as X-Shopify-Access-Token (https://shopify.dev/docs/api/partner/latest).
- `PLATFORM_MCP_SHOPIFY_APP_STORE_ORGANIZATION_ID` — Partner organization id from the Partners Dashboard URL (https://partners.shopify.com/{organization_id}/...); part of every endpoint URL.

## Run

    uvx platform-mcp-hub serve shopify_app_store          # Python
    npx -y platform-mcp-hub serve shopify_app_store       # TypeScript
    claude mcp add shopify_app_store -- uvx platform-mcp-hub serve shopify_app_store

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/shopify_app_store-mcp`. Python and TypeScript serve identical tools.
