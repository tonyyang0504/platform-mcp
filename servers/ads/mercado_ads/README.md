# Mercado Ads (Mercado Libre Publicidad) MCP server

Category: **ads** · Docs: https://developers.mercadolibre.com.ar/en_us/product-ads-us-read · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/mercado_ads.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /users/me` (https://developers.mercadolibre.com.ar/en_us/authentication-and-authorization)
- `list_accounts` — `GET /advertising/advertisers` (https://developers.mercadolibre.com.ar/en_us/product-ads-us-read)
- `list_campaigns` — `GET /advertising/advertisers/{account_id}/product_ads/campaigns` (https://developers.mercadolibre.com.ar/en_us/product-ads-us-read)
- `get_report` — `GET /advertising/advertisers/{account_id}/product_ads/campaigns` (https://developers.mercadolibre.com.ar/en_us/product-ads-us-read)
- ~~`update_budget`~~ not offered: Mercado Libre's public Product Ads documentation is the read-only reference ("With the following Product Ads endpoints, you can monitor campaigns, ads, and metrics", https://developers.mercadolibre.com.ar/en_us/product-ads-us-read); no campaign update endpoint is documented publicly.
- ~~`pause_resume`~~ not offered: No campaign status update endpoint is documented in the public Product Ads reference (https://developers.mercadolibre.com.ar/en_us/product-ads-us-read), which only covers reading campaigns, ads and metrics.

## Credentials

- `PLATFORM_MCP_MERCADO_ADS_CLIENT_ID` — App ID of your application (developers.mercadolibre.com > My applications); sent as client_id in the token request body.
- `PLATFORM_MCP_MERCADO_ADS_CLIENT_SECRET` — Secret Key of the same application; sent as client_secret in the token request body.
- `PLATFORM_MCP_MERCADO_ADS_REFRESH_TOKEN` — Refresh token (TG-...) from a one-time authorization-code consent by the advertiser's ADMIN account (Product Ads enabled under Mi perfil > Publicidad) (valid 6 months). It is SINGLE-USE: every refresh returns a new access token (6 h) and a new refresh token, and only the last one issued is accepted. The runtime keeps a rotated refresh token in memory; set PLATFORM_MCP_STATE_DIR to also save it (<dir>/<platform>.json, mode 0600) so it is preferred over this variable on the next start. Without the state directory, a restart after the first refresh needs a fresh refresh token.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve mercado_ads   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve mercado_ads
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve mercado_ads   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/mercado_ads-mcp`. Python and TypeScript serve identical tools.
