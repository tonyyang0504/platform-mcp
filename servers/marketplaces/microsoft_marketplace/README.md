# Microsoft Marketplace / AppSource MCP server

Category: **marketplaces** · Docs: https://learn.microsoft.com/en-us/partner-center/marketplace-offers/product-ingestion-api · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/marketplaces/microsoft_marketplace.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /product` (https://learn.microsoft.com/en-us/partner-center/marketplace-offers/product-ingestion-api)
- `list_products` — `GET /product` (https://learn.microsoft.com/en-us/partner-center/marketplace-offers/product-ingestion-api)
- `get_product` — `GET /{product_id}` (https://learn.microsoft.com/en-us/partner-center/marketplace-offers/product-ingestion-api)
- ~~`create_product`~~ not offered: Products are created through POST configure?$version= with a configure document of typed resources (product, property, listing, plan, price-and-availability...) that runs as an asynchronous job ('Configure status ... GET configure/<jobID>/status') - one call cannot build or confirm it.
- ~~`update_price`~~ not offered: Prices live in each plan's price-and-availability resource submitted through the asynchronous configure job (retrieve the resource tree, change it, POST configure, poll configure/<jobID>/status), not a single price call.
- ~~`list_sales`~~ not offered: Marketplace orders come from the Partner Center analytics programmatic-access API, an asynchronous scheduled-report flow (create query, schedule report, poll, download CSV) the adapter cannot follow.
- ~~`get_sales_stats`~~ not offered: Revenue is only available as scheduled Partner Center analytics reports (asynchronous report polling and CSV download).
- ~~`list_refunds`~~ not offered: No refund collection in the Product Ingestion API; refunds appear only in Partner Center payout reports.
- ~~`refund`~~ not offered: Customers' marketplace purchases are refunded by Microsoft support, not by a publisher API.

## Credentials

- `PLATFORM_MCP_MICROSOFT_MARKETPLACE_CLIENT_ID` — Microsoft Entra application (client) ID added to the Partner Center account.
- `PLATFORM_MCP_MICROSOFT_MARKETPLACE_CLIENT_SECRET` — Client secret of that Entra application.
- `PLATFORM_MCP_MICROSOFT_MARKETPLACE_TENANT_ID` — Microsoft Entra tenant ID of the publisher (Partner Center > Account settings).

## Run

    uvx platform-mcp-hub serve microsoft_marketplace          # Python
    npx -y platform-mcp-hub serve microsoft_marketplace       # TypeScript
    claude mcp add microsoft_marketplace -- uvx platform-mcp-hub serve microsoft_marketplace

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/microsoft_marketplace-mcp`. Python and TypeScript serve identical tools.
