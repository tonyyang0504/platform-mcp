# DHgate MCP server

Category: **ecommerce_suppliers** · Docs: https://open.dhgate.com/docs/api · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_suppliers/dhgate.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /dop/router` (https://open.dhgate.com/docs/api/detail/7b539fd675694fcb8c7931b333f4c0cc)
- `list_products` — `GET /dop/router` (https://open.dhgate.com/docs/api/detail/be9ac51528414982a551a1f0a58ce512)
- `get_product` — `GET /dop/router` (https://open.dhgate.com/docs/api/detail/adfcb535f3d74f209b735e5b3025fb8c)
- `quote_shipping` — `GET /dop/router` (https://open.dhgate.com/docs/api/detail/50cda2405433480dacabefbde31fd780)
- `create_order` — `POST /dop/router` (https://open.dhgate.com/docs/api/detail/d57650c0b5424bf981d12a8f08653115)
- `get_order` — `GET /dop/router` (https://open.dhgate.com/docs/api/detail/1231fa83e6094cbab75d3a8d27913776)
- ~~`track`~~ not offered: No tracking-events call: dh.buyer.trade.order.status.get (https://open.dhgate.com/docs/api/detail/fab4906ab8014172935302925706bea3) and dh.buyer.trade.deliveryno.get return only the order status and deliveryNo, 'Format: [transport mode: shipping No.; ...]. Example: UPS:DY0124,DHL:301245' (one string, no events); the shipping numbers are already in get_order.

## Credentials

- `PLATFORM_MCP_DHGATE_CLIENT_ID` — App Key of your DHgate Open Platform application (https://open.dhgate.com/console); the Dropshipping/buyer APIs must be granted to the app (API authorization level A, no public network access).
- `PLATFORM_MCP_DHGATE_CLIENT_SECRET` — App Secret of the application, sent in the refresh_token grant to https://secure.dhgate.com/dop/oauth2/access_token.
- `PLATFORM_MCP_DHGATE_REFRESH_TOKEN` — Refresh token from the DHgate BUYER account's authorization-code consent (https://secure.dhgate.com/dop/oauth2/authorize?response_type=code&client_id=…&scope=basic, then grant_type=authorization_code). It is valid 30 days; the runtime mints 1-day access tokens from it and keeps the refresh_token each response returns (set PLATFORM_MCP_STATE_DIR to persist it).

## Run

    uvx platform-mcp-hub serve dhgate          # Python
    npx -y platform-mcp-hub serve dhgate       # TypeScript
    claude mcp add dhgate -- uvx platform-mcp-hub serve dhgate

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/dhgate-mcp`. Python and TypeScript serve identical tools.
