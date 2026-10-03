# Zalando Partner Program MCP server

Category: **ecommerce_channels** · Docs: https://partner.zalando.com/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_channels/zalando.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /auth/me` (https://developers.merchants.zalando.com/docs/openapi/authentication.html)
- `update_listing` — `POST /merchants/{mid}/prices` (https://developers.merchants.zalando.com/docs/offers-prices-api.html)
- `set_inventory` — `POST /merchants/{mid}/stocks` (https://developers.merchants.zalando.com/docs/offers-stocks-api.html)
- `end_listing` — `POST /merchants/{mid}/offer-blockers` (https://developers.merchants.zalando.com/docs/offers-blocking.html)
- `list_orders` — `GET /merchants/{mid}/orders` (https://developers.merchants.zalando.com/docs/orders-api-get-orders.html)
- `mark_shipped` — `PATCH /merchants/{mid}/orders/{order_id}` (https://developers.merchants.zalando.com/docs/orders-api-patch.html)
- ~~`create_listing`~~ not offered: Offers are created by onboarding products (Product Submission / Onboarding APIs with the category's attribute model per EAN) and then sending prices and stocks per sales channel; the vocabulary has no EAN attributes or product model.

## Credentials

- `PLATFORM_MCP_ZALANDO_CLIENT_ID` — Client ID of an app registered in the zDirect (Zalando Partner) portal > Applications, with the stocks, prices, orders and offer-blocker scopes granted.
- `PLATFORM_MCP_ZALANDO_CLIENT_SECRET` — Client secret of the same app; sent with the client ID as HTTP Basic on POST https://api.merchants.zalando.com/auth/token.
- `PLATFORM_MCP_ZALANDO_MERCHANT_ID` — Your zDirect merchant id (uuid; GET /auth/me lists the merchant ids the token can access).
- `PLATFORM_MCP_ZALANDO_SALES_CHANNEL_ID` — Sales channel id (uuid) the offers belong to (Sales Channels API); each Zalando country shop is a channel.
- `PLATFORM_MCP_ZALANDO_CURRENCY` — ISO currency of the sales channel, e.g. EUR; required for update_listing.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve zalando   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve zalando
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve zalando   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/zalando-mcp`. Python and TypeScript serve identical tools.
