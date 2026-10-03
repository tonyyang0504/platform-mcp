# OTTO Advertising (OTTO Retail Media) MCP server

Category: **ads** · Docs: https://api.otto.market/docs/functional-interfaces/sponsored-product-ads · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/otto_retail_media.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /v1/sponsored-product-ads/campaigns` (https://api.otto.market/docs/functional-interfaces/sponsored-product-ads)
- `list_campaigns` — `GET /v1/sponsored-product-ads/campaigns` (https://api.otto.market/docs/functional-interfaces/sponsored-product-ads)
- `update_budget` — `PATCH /v1/sponsored-product-ads/campaigns/{campaign_id}` (https://api.otto.market/docs/functional-interfaces/sponsored-product-ads)
- `pause_resume` — `PATCH /v1/sponsored-product-ads/campaigns/{campaign_id}` (https://api.otto.market/docs/functional-interfaces/sponsored-product-ads)
- ~~`list_accounts`~~ not offered: The token's partner identity determines the data ("There is no need to pass the partner identity as a parameter; it is derived from the token", https://api.otto.market/docs/functional-interfaces/sponsored-product-ads-reporting); there is no account listing.
- ~~`get_report`~~ not offered: Synchronous "GET /v1/spa-reporting/campaign-performance" returns one totals object per campaign (not rows) and full reports are asynchronous CSV jobs polled by reportId (https://api.otto.market/docs/functional-interfaces/sponsored-product-ads-reporting); the runtime can neither wrap a single object as rows nor poll and download CSV reports.

## Credentials

- `PLATFORM_MCP_OTTO_RETAIL_MEDIA_CLIENT_ID` — Client ID of a self-app created in OTTO Partner Connect > API-Zugriff with the advertising-services scope (https://api.otto.market/docs/sellers-integration).
- `PLATFORM_MCP_OTTO_RETAIL_MEDIA_CLIENT_SECRET` — The app's client secret (shown once in OPC). Tokens last 1800 s and are re-minted with the client credentials (no refresh token).

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve otto_retail_media   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve otto_retail_media
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve otto_retail_media   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/otto_retail_media-mcp`. Python and TypeScript serve identical tools.
