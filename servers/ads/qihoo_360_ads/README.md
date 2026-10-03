# 360 点睛营销平台 360 Ads MCP server

Category: **ads** · Docs: https://open.e.360.cn/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/qihoo_360_ads.json`; edit the catalog, not this file.

## Tools

- `me` — `POST /uc/account/getInfo` (https://open.e.360.cn/api/account_getInfo.html)
- `get_report` — `POST /dianjing/report/campaign` (https://open.e.360.cn/api/report_campaign.html)
- `update_budget` — `POST /dianjing/campaign/update` (https://open.e.360.cn/api/campaign_update.html)
- `pause_resume` — `POST /dianjing/campaign/update` (https://open.e.360.cn/api/campaign_update.html)
- ~~`list_accounts`~~ not offered: clientLogin issues a token for one 点睛 account ('作为操作对应广告账户的凭证', https://open.e.360.cn/api/account_clientLogin.html); listing accounts (account_getmccuserlist) needs the separate agency managerLogin flow.
- ~~`list_campaigns`~~ not offered: Campaign details come in two calls: getCampaignIdList returns only a bare id array ('campaignIdList: 推广计划id数组', https://open.e.360.cn/api/campaign_getCampaignIdList.html) and campaign/getInfoByIdList needs those ids ('idList … json格式的id数组', https://open.e.360.cn/api/campaign_getInfoByIdList.html); a single adapter call cannot chain them and the runtime keeps only object rows.

## Credentials

- `PLATFORM_MCP_QIHOO_360_ADS_API_KEY` — ApiKey e-mailed after the open.e.360.cn developer application is approved; sent as the `apiKey` HTTP header on every call.
- `PLATFORM_MCP_QIHOO_360_ADS_USERNAME` — 360 点睛 account login name (clientLogin `username`).
- `PLATFORM_MCP_QIHOO_360_ADS_ENCRYPTED_PASSWORD` — clientLogin `passwd`: AES-CBC(MD5(password)) with key = first 16 characters of the ApiSecret and IV = last 16, as 64 lowercase hex characters (身份认证: '秘钥是apiSecret 的前16位，向量是后16位'). It is a fixed value, so compute it once with 360's official 'openAPI登录接口AES调试工具' or its code samples; the password itself is never needed. Five wrong logins lock the account until the next day.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve qihoo_360_ads   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve qihoo_360_ads
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve qihoo_360_ads   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/qihoo_360_ads-mcp`. Python and TypeScript serve identical tools.
