# 腾讯广告 Tencent Ads MCP server

Category: **ads** · Docs: https://developers.e.qq.com/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/tencent_ads.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /advertiser/get` (https://developers.e.qq.com/v3.0/docs/api/advertiser/get)
- `list_accounts` — `GET /advertiser/get` (https://developers.e.qq.com/v3.0/docs/api/advertiser/get)
- `list_campaigns` — `GET /adgroups/get` (https://developers.e.qq.com/v3.0/docs/api/adgroups/get)
- `get_report` — `GET /daily_reports/get` (https://developers.e.qq.com/v3.0/docs/api/daily_reports/get)
- `update_budget` — `POST /adgroups/update` (https://developers.e.qq.com/v3.0/docs/api/adgroups/update)
- `pause_resume` — `POST /adgroups/update` (https://developers.e.qq.com/v3.0/docs/api/adgroups/update)

## Credentials

- `PLATFORM_MCP_TENCENT_ADS_CLIENT_ID` — 应用 id (client_id) of your Tencent Marketing API application (developers.e.qq.com > 应用程序管理).
- `PLATFORM_MCP_TENCENT_ADS_CLIENT_SECRET` — 应用 secret (client_secret) of the same application.
- `PLATFORM_MCP_TENCENT_ADS_REFRESH_TOKEN` — refresh_token from the one-time OAuth consent (oauth/authorize → GET https://api.e.qq.com/oauth/token?grant_type=authorization_code). The runtime mints 1-day access tokens with grant_type=refresh_token; the refresh token itself expires after refresh_token_expires_in (30 days) and must then be re-authorized.
- `PLATFORM_MCP_TENCENT_ADS_ACCOUNT_ID` — 推广帐号 id (account_id) the token may operate; used by `me` and by update_budget / pause_resume (adgroups/update needs account_id). For agency tokens use the sub-account id to operate.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve tencent_ads   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve tencent_ads
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve tencent_ads   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/tencent_ads-mcp`. Python and TypeScript serve identical tools.
