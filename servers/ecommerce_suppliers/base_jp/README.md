# BASE (store platform) + BASE Developers API + BASE Apps supplier connectors MCP server

Category: **ecommerce_suppliers** · Docs: https://apps.thebase.com/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_suppliers/base_jp.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /1/users/me` (https://docs.thebase.in/api/users/me)
- `list_products` — `GET /1/items` (https://docs.thebase.in/api/items/)
- `get_product` — `GET /1/items/detail/{id}` (https://docs.thebase.in/api/items/detail)
- `get_order` — `GET /1/orders/detail/{id}` (https://docs.thebase.in/api/orders/detail)
- ~~`quote_shipping`~~ not offered: BASE is the merchant's own storefront; the API index (https://docs.thebase.in/api/) has Users, Items, Categories, Orders, Savings, Delivery Company and Search endpoints and no shipping-rate calculation.
- ~~`create_order`~~ not offered: Orders are placed by shoppers on the storefront; the API offers only 'GET /1/orders', 'GET /1/orders/detail/:unique_key' and 'POST /1/orders/edit_status' (https://docs.thebase.in/api/), no order creation.
- ~~`track`~~ not offered: No shipment-tracking endpoint exists (https://docs.thebase.in/api/); the order's tracking_number and dispatch_status are returned by get_order.

## Credentials

- `PLATFORM_MCP_BASE_JP_CLIENT_ID` — Client ID of your app at https://developers.thebase.in/ (API application required).
- `PLATFORM_MCP_BASE_JP_CLIENT_SECRET` — Client secret of the same app.
- `PLATFORM_MCP_BASE_JP_REFRESH_TOKEN` — Refresh token from the one-time authorization-code exchange (GET /1/oauth/authorize with scope read_users read_items read_orders → POST /1/oauth/token, https://docs.thebase.in/api/oauth/access_token). Valid about 30 days and rotated on every refresh; set PLATFORM_MCP_STATE_DIR so the rotated token survives restarts.
- `PLATFORM_MCP_BASE_JP_REDIRECT_URI` — The callback URL registered for your BASE Developers app; BASE requires it in every refresh-token request ('redirect_uri 登録したコールバックURL (必須)', https://docs.thebase.in/api/oauth/refresh_token).

## Run

    uvx platform-mcp-hub serve base_jp          # Python
    npx -y platform-mcp-hub serve base_jp       # TypeScript
    claude mcp add base_jp -- uvx platform-mcp-hub serve base_jp

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/base_jp-mcp`. Python and TypeScript serve identical tools.
