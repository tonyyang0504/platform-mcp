# 鲸鸿动能 Petal Ads (Huawei Ads) MCP server

Category: **ads** · Docs: https://developer.huawei.com/consumer/cn/doc/promotion/ads_api02-0000001058566534 · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/huawei_ads.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /openapi/v2/promotion/campaign/query` (https://developer.huawei.com/consumer/cn/doc/promotion/ads_api19-0000001057938573)
- `list_accounts` — `GET /openapi/v2/manager/advertiser/query` (https://developer.huawei.com/consumer/cn/doc/promotion/ads_api_jlzh1-0000001229444855)
- `list_campaigns` — `GET /openapi/v2/promotion/campaign/query` (https://developer.huawei.com/consumer/cn/doc/promotion/ads_api19-0000001057938573)
- `get_report` — `POST /openapi/v2/reports/campaign/query` (https://developer.huawei.com/consumer/cn/doc/promotion/ads_api67-0000001057938581)
- `update_budget` — `POST /ads/v1/promotion/campaign/update` (https://developer.huawei.com/consumer/cn/doc/promotion/ads_new_api05-0000001455960409)
- `pause_resume` — `POST /ads/v1/promotion/campaign/update` (https://developer.huawei.com/consumer/cn/doc/promotion/ads_new_api05-0000001455960409)

## Credentials

- `PLATFORM_MCP_HUAWEI_ADS_CLIENT_ID` — Your Marketing API client ID (华为开发者联盟 → 申请客户端ID).
- `PLATFORM_MCP_HUAWEI_ADS_CLIENT_SECRET` — The client secret shown for that client ID in the developer alliance.
- `PLATFORM_MCP_HUAWEI_ADS_REFRESH_TOKEN` — refresh_token from the authorization-code login (authorize with access_type=offline and the ads scopes, then exchange the code at /oauth2/v2/token), see ads_api09.
- `PLATFORM_MCP_HUAWEI_ADS_ADVERTISER_ID` — Advertiser ID; required when the authorizing Huawei ID is a manager (经理) account, a service-provider account or linked to several sub-client advertisers.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve huawei_ads   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve huawei_ads
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve huawei_ads   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/huawei_ads-mcp`. Python and TypeScript serve identical tools.
