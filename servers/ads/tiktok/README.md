# TikTok for Business (TikTok Ads Manager) MCP server

Category: **ads** · Docs: https://business-api.tiktok.com/portal/docs · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/tiktok.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /oauth2/advertiser/get/` (https://business-api.tiktok.com/portal/docs/get-authorized-ad-accounts/v1.3)
- `list_accounts` — `GET /oauth2/advertiser/get/` (https://business-api.tiktok.com/portal/docs/get-authorized-ad-accounts/v1.3)
- `list_campaigns` — `GET /campaign/get/` (https://business-api.tiktok.com/portal/docs/get-campaigns/v1.3)
- `get_report` — `GET /report/integrated/get/` (https://business-api.tiktok.com/portal/docs/run-a-synchronous-report/v1.3)
- `update_budget` — `POST /campaign/update/` (https://business-api.tiktok.com/portal/docs/update-a-campaign/v1.3)
- `pause_resume` — `POST /campaign/status/update/` (https://business-api.tiktok.com/portal/docs/update-campaign-status/v1.3)

## Credentials

- `PLATFORM_MCP_TIKTOK_ACCESS_TOKEN` — Long-term advertiser access token from the TikTok API for Business authorization flow (/oauth2/access_token/), sent as the `Access-Token` header.
- `PLATFORM_MCP_TIKTOK_APP_ID` — Developer app id (Application Management page); sent as a query parameter only to /oauth2/advertiser/get/ (me, list_accounts).
- `PLATFORM_MCP_TIKTOK_SECRET` — The developer app's secret, sent as the `secret` query parameter only to /oauth2/advertiser/get/ (me, list_accounts).
- `PLATFORM_MCP_TIKTOK_ADVERTISER_ID` — Advertiser (ad account) id that update_budget writes to (campaign/update requires advertiser_id in the body).

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve ads/tiktok   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve ads/tiktok
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve ads/tiktok   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/tiktok-ads-mcp`. Python and TypeScript serve identical tools.
