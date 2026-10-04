# Google Merchant Center MCP server

Category: **ecommerce_channels** · Docs: https://developers.google.com/merchant/api/overview · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_channels/google_merchant.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /accounts/v1/accounts/{acct}` (https://developers.google.com/merchant/api/reference/rest/accounts_v1/accounts/get)
- `update_listing` — `PATCH /products/v1/accounts/{acct}/productInputs/{pi}` (https://developers.google.com/merchant/api/reference/rest/products_v1/accounts.productInputs/patch)
- `end_listing` — `DELETE /products/v1/accounts/{acct}/productInputs/{pi}` (https://developers.google.com/merchant/api/reference/rest/products_v1/accounts.productInputs/delete)
- ~~`create_listing`~~ not offered: productInputs.insert requires the price as Price {amountMicros (int64 string), currencyCode} plus link, imageLink and availability; converting the vocabulary's decimal price into micros needs arithmetic the declarative adapter does not have, and the vocabulary has no product page link.
- ~~`set_inventory`~~ not offered: Merchant Center products carry an availability state, not a stock quantity (quantities exist only for local inventory per store code); no call sets a stock count for an online offer.
- ~~`list_orders`~~ not offered: The Merchant API has no orders resource (checkout happens on the merchant's own site).
- ~~`mark_shipped`~~ not offered: No orders or shipments in the Merchant API.

## Credentials

- `PLATFORM_MCP_GOOGLE_MERCHANT_CLIENT_ID` — OAuth 2.0 client ID of your Google Cloud project (with the Merchant API enabled and the project registered with the Merchant Center account).
- `PLATFORM_MCP_GOOGLE_MERCHANT_CLIENT_SECRET` — OAuth client secret of the same client.
- `PLATFORM_MCP_GOOGLE_MERCHANT_REFRESH_TOKEN` — Refresh token from a one-time consent with scope https://www.googleapis.com/auth/content by a user of the Merchant Center account; the runtime mints access tokens at https://oauth2.googleapis.com/token.
- `PLATFORM_MCP_GOOGLE_MERCHANT_ACCOUNT_ID` — Numeric Merchant Center account id.
- `PLATFORM_MCP_GOOGLE_MERCHANT_DATA_SOURCE` — API product data source to write to, in the form accounts/<account>/dataSources/<id> (Merchant Center > Data sources, or the Data Sources API); only API data sources can be edited.
- `PLATFORM_MCP_GOOGLE_MERCHANT_CONTENT_LANGUAGE` — Two-letter content language of your products, e.g. en; part of the product input id <language>~<feedLabel>~<offerId>.
- `PLATFORM_MCP_GOOGLE_MERCHANT_FEED_LABEL` — Feed label of your products, e.g. US; part of the product input id.

## Run

    uvx platform-mcp-hub serve google_merchant          # Python
    npx -y platform-mcp-hub serve google_merchant       # TypeScript
    claude mcp add google_merchant -- uvx platform-mcp-hub serve google_merchant

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/google_merchant-mcp`. Python and TypeScript serve identical tools.
