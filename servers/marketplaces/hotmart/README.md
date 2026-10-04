# Hotmart MCP server

Category: **marketplaces** · Docs: https://developers.hotmart.com · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/marketplaces/hotmart.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /user/api/v1/me` (https://developers.hotmart.com/docs/en/v1/user/get-user-me/)
- `list_products` — `GET /products/api/v1/products` (https://developers.hotmart.com/docs/en/v1/product/product-list/)
- `get_product` — `GET /products/api/v1/products` (https://developers.hotmart.com/docs/en/v1/product/product-list/)
- `list_sales` — `GET /payments/api/v1/sales/history` (https://developers.hotmart.com/docs/en/v1/sales/sales-history/)
- `get_sales_stats` — `GET /payments/api/v1/sales/summary` (https://developers.hotmart.com/docs/en/v1/sales/sales-summary/)
- `list_refunds` — `GET /payments/api/v1/sales/history` (https://developers.hotmart.com/docs/en/v1/sales/sales-history/)
- `refund` — `PUT /payments/api/v1/sales/{sale_id}/refund` (https://developers.hotmart.com/docs/en/v1/sales/sales-refund/)
- ~~`create_product`~~ not offered: Products are created in the Hotmart dashboard; the product API documents only listing, offers, plans and PUT /products/api/v1/product/configuration/:product_id (is_allowed_to_email_the_buyer).
- ~~`update_price`~~ not offered: Prices belong to offers (GET /products/api/v1/products/:ucode/offers is read-only); no endpoint changes an offer's price.

## Credentials

- `PLATFORM_MCP_HOTMART_CLIENT_ID` — Client ID from Hotmart Tools > Developer Credentials.
- `PLATFORM_MCP_HOTMART_CLIENT_SECRET` — Client Secret from the same credential.
- `PLATFORM_MCP_HOTMART_BASIC_TOKEN` — The 'Basic' value shown with the credential (without the 'Basic ' prefix).

## Run

    uvx platform-mcp-hub serve hotmart          # Python
    npx -y platform-mcp-hub serve hotmart       # TypeScript
    claude mcp add hotmart -- uvx platform-mcp-hub serve hotmart

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/hotmart-mcp`. Python and TypeScript serve identical tools.
