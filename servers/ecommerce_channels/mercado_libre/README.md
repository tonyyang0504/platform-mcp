# Mercado Libre MCP server

Category: **ecommerce_channels** · Docs: https://developers.mercadolibre.com/en_us/authentication-and-authorization · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_channels/mercado_libre.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /users/me` (https://developers.mercadolibre.com.ar/en_us/authentication-and-authorization)
- `update_listing` — `PUT /items/{listing_id}` (https://developers.mercadolibre.com.ar/en_us/products-sync-listings)
- `end_listing` — `PUT /items/{listing_id}` (https://developers.mercadolibre.com.ar/en_us/products-sync-listings)
- `set_inventory` — `PUT /items/{listing_id}` (https://developers.mercadolibre.com.ar/en_us/products-sync-listings)
- `list_orders` — `GET /orders/search` (https://developers.mercadolibre.com.ar/en_us/manage-sales)
- ~~`create_listing`~~ not offered: POST /items requires category_id (predicted per product), listing_type_id, currency_id, condition, buying_mode, pictures and the category's required attributes (BRAND, MODEL, GTIN, ...) — none of which the vocabulary carries; the category attributes differ per category.
- ~~`mark_shipped`~~ not offered: Marking an ME1 (seller-shipped) order as dispatched is POST /shipments/{shipment_id}/seller_notifications {payload{service_id (per site), comment, date}, tracking_number, tracking_url, status: shipped, substatus: null}; the shipment id comes from GET /orders/{order_id}/shipments first (two calls). Mercado Envíos ME2 shipments are tracked by the carrier.
- ~~`listing_metrics`~~ not offered: No per-item visits endpoint confirmed this pass (the visits documentation page did not load); not mapped.

## Credentials

- `PLATFORM_MCP_MERCADO_LIBRE_CLIENT_ID` — App ID of your application (developers.mercadolibre.com > My applications); sent as client_id in the token request body.
- `PLATFORM_MCP_MERCADO_LIBRE_CLIENT_SECRET` — Secret Key of the same application; sent as client_secret in the token request body.
- `PLATFORM_MCP_MERCADO_LIBRE_REFRESH_TOKEN` — Refresh token (TG-...) from a one-time authorization-code consent by the seller's ADMIN account (valid 6 months). It is SINGLE-USE: every refresh returns a new access token (6 h) and a new refresh token, and only the last one issued is accepted. The runtime keeps a rotated refresh token in memory; set PLATFORM_MCP_STATE_DIR to also save it (<dir>/<platform>.json, mode 0600) so it is preferred over this variable on the next start. Without the state directory, a restart after the first refresh needs a fresh refresh token.
- `PLATFORM_MCP_MERCADO_LIBRE_SELLER_ID` — Numeric Mercado Libre user id of the seller (the `id` returned by GET /users/me); used as the seller filter of the order search.
- `PLATFORM_MCP_MERCADO_LIBRE_ENV` — Vendor environment (default production): sandbox = production host with test accounts or test keys. Credentials are the environment's own; see adapter.environments in the catalog entry.
- `PLATFORM_MCP_MERCADO_LIBRE_BASE_URL` — Optional https base URL override (a mock or a private gateway); replaces the selected environment's base_url. Never echoed in errors.

## Run

    uvx platform-mcp-hub serve ecommerce_channels/mercado_libre          # Python
    npx -y platform-mcp-hub serve ecommerce_channels/mercado_libre       # TypeScript
    claude mcp add mercado_libre -- uvx platform-mcp-hub serve ecommerce_channels/mercado_libre

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/mercado_libre-ecommerce-channels-mcp`. Python and TypeScript serve identical tools.
