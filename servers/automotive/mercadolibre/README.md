# Mercado Libre Autos MCP server

Category: **automotive** · Docs: https://developers.mercadolibre.com.ar/en_us/items-and-searches · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/automotive/mercadolibre.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /users/me` (https://developers.mercadolibre.com.ar/en_us/authentication-and-authorization)
- `get_listing` — `GET /items/{listing_id}` (https://developers.mercadolibre.com.ar/en_us/list-vehicles)
- ~~`search_listings`~~ not offered: Items & Searches (updated 04/04/2025) documents /sites/{site_id}/search only by seller_id/nickname and replaces it with /users/{id}/items/search (the caller's own items); no keyword or category listing search is documented, so none is served.
- ~~`decode_vin`~~ not offered: No VIN decoder in the Mercado Libre API.
- ~~`get_valuation`~~ not offered: No valuation endpoint in the Mercado Libre API.
- ~~`list_dealers`~~ not offered: No dealer directory endpoint in the Mercado Libre API.

## Credentials

- `PLATFORM_MCP_MERCADOLIBRE_CLIENT_ID` — App ID of your application (developers.mercadolibre.com > My applications); sent as client_id in the token request body.
- `PLATFORM_MCP_MERCADOLIBRE_CLIENT_SECRET` — Secret Key of the same application; sent as client_secret in the token request body.
- `PLATFORM_MCP_MERCADOLIBRE_REFRESH_TOKEN` — Refresh token (TG-...) from a one-time authorization-code consent of any Mercado Libre account to your app (valid 6 months). It is SINGLE-USE: every refresh returns a new access token (6 h) and a new refresh token, and only the last one issued is accepted. The runtime keeps a rotated refresh token in memory; set PLATFORM_MCP_STATE_DIR to also save it (<dir>/mercadolibre.json, mode 0600) so it is preferred over this variable on the next start. Do not share one refresh token between this server and the ecommerce/marketplaces Mercado Libre servers.
- `PLATFORM_MCP_MERCADOLIBRE_ENV` — Vendor environment (default production): sandbox = production host with test accounts or test keys. Credentials are the environment's own; see adapter.environments in the catalog entry.
- `PLATFORM_MCP_MERCADOLIBRE_BASE_URL` — Optional https base URL override (a mock or a private gateway); replaces the selected environment's base_url. Never echoed in errors.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve mercadolibre   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve mercadolibre
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve mercadolibre   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/mercadolibre-mcp`. Python and TypeScript serve identical tools.
