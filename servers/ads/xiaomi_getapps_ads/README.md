# 小米营销 Xiaomi Ads MCP server

Category: **ads** · Docs: https://global.e.mi.com/doc/zh/marketing_api_guide.html · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/xiaomi_getapps_ads.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /foreign/marketing/region/countryList` (https://global.e.mi.com/doc/zh/marketing_api_guide.html)
- `list_campaigns` — `GET /foreign/marketing/campaign/list` (https://global.e.mi.com/doc/zh/marketing_api_guide.html)
- `update_budget` — `POST /foreign/marketing/group/update` (https://global.e.mi.com/doc/zh/marketing_api_guide.html)
- ~~`list_accounts`~~ not offered: No account-listing call is documented: the guide covers token creation, common parameters, 广告计划 (list/add), 广告组 (list/add/update, regions, media) and 广告创意 (list/add/update, upload) (https://global.e.mi.com/doc/zh/marketing_api_guide.html); accounts are those the AM enabled for the app.
- ~~`get_report`~~ not offered: No reporting endpoint is documented in the Marketing API guide (sections 一 申请创建外部应用 … 四 广告接口介绍: 广告计划, 广告组, 广告创意; https://global.e.mi.com/doc/zh/marketing_api_guide.html).
- ~~`pause_resume`~~ not offered: No status field or pause/resume call is documented: 2.3 修改广告组 accepts only groupIds, regions, dayBudget and bid, and campaigns have only list/add (https://global.e.mi.com/doc/zh/marketing_api_guide.html).

## Credentials

- `PLATFORM_MCP_XIAOMI_GETAPPS_ADS_APP_ID` — appId of the external application your Xiaomi account manager (AM) created when Marketing API access was approved ('申请通过后，AM提供appId、appKey等应用信息').
- `PLATFORM_MCP_XIAOMI_GETAPPS_ADS_APP_KEY` — appKey of that application; exchanged for an access token with POST /foreign/token/createToken.

## Run

    uvx platform-mcp-hub serve xiaomi_getapps_ads          # Python
    npx -y platform-mcp-hub serve xiaomi_getapps_ads       # TypeScript
    claude mcp add xiaomi_getapps_ads -- uvx platform-mcp-hub serve xiaomi_getapps_ads

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/xiaomi_getapps_ads-mcp`. Python and TypeScript serve identical tools.
