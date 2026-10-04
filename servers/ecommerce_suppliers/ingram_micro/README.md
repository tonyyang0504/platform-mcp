# Ingram Micro (Xvantage / Developer Portal) MCP server

Category: **ecommerce_suppliers** · Docs: https://developer.ingrammicro.com/reseller · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_suppliers/ingram_micro.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /resellers/v6/catalog` (https://developer.ingrammicro.com/reseller/api-documentation/United_States)
- `list_products` — `GET /resellers/v6/catalog` (https://developer.ingrammicro.com/reseller/api-documentation/United_States)
- `get_product` — `GET /resellers/v6/catalog/details/{id}` (https://developer.ingrammicro.com/reseller/api-documentation/United_States)
- `quote_shipping` — `POST /resellers/v6/freightestimate` (https://developer.ingrammicro.com/reseller/api-documentation/United_States)
- `create_order` — `POST /resellers/v6/orders` (https://developer.ingrammicro.com/reseller/api-documentation/United_States)
- `get_order` — `GET /resellers/v6.1/orders/{id}` (https://developer.ingrammicro.com/reseller/api-documentation/United_States)
- `track` — `GET /resellers/v6.1/orders/{order_id}` (https://developer.ingrammicro.com/reseller/api-documentation/United_States)

## Credentials

- `PLATFORM_MCP_INGRAM_MICRO_CLIENT_ID` — Client ID (Consumer Key) of your app on developer.ingrammicro.com (My Apps); production keys after app approval.
- `PLATFORM_MCP_INGRAM_MICRO_CLIENT_SECRET` — Client Secret of the same app; exchanged for a bearer token at /oauth/oauth30/token (client_credentials).
- `PLATFORM_MCP_INGRAM_MICRO_CUSTOMER_NUMBER` — Your Ingram Micro reseller customer number (IM-CustomerNumber header, e.g. 20-222222).
- `PLATFORM_MCP_INGRAM_MICRO_COUNTRY_CODE` — Two-letter ISO country of your Ingram Micro account (IM-CountryCode header, e.g. US).
- `PLATFORM_MCP_INGRAM_MICRO_SENDER_ID` — Optional sender identification text (IM-SenderID header, max 32 chars).
- `PLATFORM_MCP_INGRAM_MICRO_CUSTOMER_CONTACT` — E-mail of the logged-in user (IM-CustomerContact header); required by Freight Estimate (quote_shipping).

## Run

    uvx platform-mcp-hub serve ingram_micro          # Python
    npx -y platform-mcp-hub serve ingram_micro       # TypeScript
    claude mcp add ingram_micro -- uvx platform-mcp-hub serve ingram_micro

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/ingram_micro-mcp`. Python and TypeScript serve identical tools.
