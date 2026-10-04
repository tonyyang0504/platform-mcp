# Atlassian Marketplace MCP server

Category: **marketplaces** · Docs: https://developer.atlassian.com/platform/marketplace/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/marketplaces/atlassian_marketplace.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /vendors/{vendor_id}/reporting/sales/transactions` (https://developer.atlassian.com/platform/marketplace/rest/v2/api-group-reporting/#api-vendors-vendorid-reporting-sales-transactions-get)
- `list_products` — `GET /addons/vendor/{vendor_id}` (https://developer.atlassian.com/platform/marketplace/rest/v2/api-group-apps/#api-addons-vendor-vendorid-get)
- `get_product` — `GET /addons/{product_id}` (https://developer.atlassian.com/platform/marketplace/rest/v2/api-group-apps/#api-addons-addonkey-get)
- `list_sales` — `GET /vendors/{vendor_id}/reporting/sales/transactions` (https://developer.atlassian.com/platform/marketplace/rest/v2/api-group-reporting/#api-vendors-vendorid-reporting-sales-transactions-get)
- `list_refunds` — `GET /vendors/{vendor_id}/reporting/sales/transactions` (https://developer.atlassian.com/platform/marketplace/rest/v2/api-group-reporting/#api-vendors-vendorid-reporting-sales-transactions-get)
- ~~`create_product`~~ not offered: App listings are created through the Marketplace partner portal / app submission flow, not a create call in the REST API v2 reporting / apps groups (https://developer.atlassian.com/platform/marketplace/rest/v2/).
- ~~`update_price`~~ not offered: Paid-via-Atlassian app prices are set per tier in the partner portal; the Apps API exposes no pricing write (https://developer.atlassian.com/platform/marketplace/rest/v2/api-group-apps/).
- ~~`get_sales_stats`~~ not offered: Aggregated sales (GET /vendors/{vendorId}/reporting/sales/transactions/{metric}) return per-period series ({total: {name, series[]}, addons[]}) by country / hosting / tier / type, not a single revenue total the vocabulary can report (https://developer.atlassian.com/platform/marketplace/rest/v2/api-group-reporting/).
- ~~`refund`~~ not offered: Refunds are processed by Atlassian (customer requests to Atlassian); the REST API only reports refund transactions (https://developer.atlassian.com/platform/marketplace/rest/v2/api-group-reporting/).

## Credentials

- `PLATFORM_MCP_ATLASSIAN_MARKETPLACE_EMAIL` — Email of the Atlassian account that belongs to the Marketplace partner (vendor) with reporting access; Basic auth username (securitySchemes mpac_authed http basic in https://developer.atlassian.com/platform/marketplace/rest/v2/ swagger.v3.json).
- `PLATFORM_MCP_ATLASSIAN_MARKETPLACE_API_TOKEN` — Atlassian API token of that account (https://id.atlassian.com/manage-profile/security/api-tokens), used as the Basic auth password.
- `PLATFORM_MCP_ATLASSIAN_MARKETPLACE_VENDOR_ID` — Numeric Marketplace partner (vendor) id, shown in the Marketplace partner portal URL (/manage/vendors/{vendorId}).

## Run

    uvx platform-mcp-hub serve atlassian_marketplace          # Python
    npx -y platform-mcp-hub serve atlassian_marketplace       # TypeScript
    claude mcp add atlassian_marketplace -- uvx platform-mcp-hub serve atlassian_marketplace

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/atlassian_marketplace-mcp`. Python and TypeScript serve identical tools.
