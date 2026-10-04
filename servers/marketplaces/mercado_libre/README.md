# Mercado Libre MCP server

Category: **marketplaces** · Docs: https://developers.mercadolibre.com · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/marketplaces/mercado_libre.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /users/me` (https://developers.mercadolibre.com.ar/en_us/authentication-and-authorization)
- `get_product` — `GET /items/{product_id}` (https://developers.mercadolibre.com.ar/en_us/items-and-searches)
- `update_price` — `PUT /items/{product_id}` (https://developers.mercadolibre.com.ar/en_us/products-sync-listings)
- `list_sales` — `GET /orders/search` (https://developers.mercadolibre.com.ar/en_us/manage-sales)
- ~~`list_products`~~ not offered: GET /users/{user_id}/items/search returns only item ids (results: ["MLA...", ...]) (https://developers.mercadolibre.com.ar/en_us/items-and-searches); names and prices need a second multiget call, which one adapter call cannot chain.
- ~~`create_product`~~ not offered: POST /items needs category_id, listing_type_id, pictures and the category's required attributes; the vocabulary carries none of them (the listing guide https://developers.mercadolibre.com.ar/en_us/products-sync-listings covers editing existing items only).
- ~~`get_sales_stats`~~ not offered: No revenue summary endpoint is documented; sales are individual orders (https://developers.mercadolibre.com.ar/en_us/manage-sales).
- ~~`list_refunds`~~ not offered: The sales guide documents orders search and order detail only; no refunds list appears there (https://developers.mercadolibre.com.ar/en_us/manage-sales).
- ~~`refund`~~ not offered: The sales guide documents no refund call for an order (https://developers.mercadolibre.com.ar/en_us/manage-sales); refunds run through Mercado Libre's claims / Mercado Pago flows, which this adapter does not map.

## Credentials

- `PLATFORM_MCP_MERCADO_LIBRE_CLIENT_ID` — App ID of your application (developers.mercadolibre.com > My applications); sent as client_id in the token request body.
- `PLATFORM_MCP_MERCADO_LIBRE_CLIENT_SECRET` — Secret Key of the same application; sent as client_secret in the token request body.
- `PLATFORM_MCP_MERCADO_LIBRE_REFRESH_TOKEN` — Refresh token (TG-...) from a one-time authorization-code consent by the seller's ADMIN account (valid 6 months). It is SINGLE-USE: every refresh returns a new access token (6 h) and a new refresh token, and only the last one issued is accepted. The runtime keeps a rotated refresh token in memory; set PLATFORM_MCP_STATE_DIR to also save it (<dir>/<platform>.json, mode 0600) so it is preferred over this variable on the next start. Without the state directory, a restart after the first refresh needs a fresh refresh token. The state file is keyed by platform id, so it is shared with ecommerce_channels/mercado_libre: give each server its own PLATFORM_MCP_STATE_DIR (or its own consent) so they never race on one single-use refresh token.
- `PLATFORM_MCP_MERCADO_LIBRE_SELLER_ID` — Numeric Mercado Libre user id of the seller (the `id` returned by GET /users/me); used as the seller filter of the order search.
- `PLATFORM_MCP_MERCADO_LIBRE_ENV` — Vendor environment (default production): sandbox = production host with test accounts or test keys. Credentials are the environment's own; see adapter.environments in the catalog entry.
- `PLATFORM_MCP_MERCADO_LIBRE_BASE_URL` — Optional https base URL override (a mock or a private gateway); replaces the selected environment's base_url. Never echoed in errors.

## Run

    uvx platform-mcp-hub serve marketplaces/mercado_libre          # Python
    npx -y platform-mcp-hub serve marketplaces/mercado_libre       # TypeScript
    claude mcp add mercado_libre -- uvx platform-mcp-hub serve marketplaces/mercado_libre

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/mercado_libre-marketplaces-mcp`. Python and TypeScript serve identical tools.
