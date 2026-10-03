# 小红书 聚光 / 蒲公英 Xiaohongshu Ads MCP server

Category: **ads** · Docs: https://ad-market.xiaohongshu.com/docs-center?bizType=943&articleId=4437 · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/xiaohongshu_pugongying.json`; edit the catalog, not this file.

## Tools

- `me` — `POST /api/open/jg/campaign/list` (https://ad-market.xiaohongshu.com/docs-center?bizType=943&articleId=3150)
- `list_campaigns` — `POST /api/open/jg/campaign/list` (https://ad-market.xiaohongshu.com/docs-center?bizType=943&articleId=3150)
- `get_report` — `POST /api/open/jg/data/report/offline/campaign` (https://ad-market.xiaohongshu.com/docs-center?bizType=943&articleId=4879)
- `update_budget` — `POST /api/open/jg/campaign/update` (https://ad-market.xiaohongshu.com/docs-center?bizType=943&articleId=3148)
- `pause_resume` — `POST /api/open/jg/campaign/status/update` (https://ad-market.xiaohongshu.com/docs-center?bizType=943&articleId=3149)
- ~~`list_accounts`~~ not offered: 聚光 MAPI has no advertiser-listing call for brand developers: the authorised advertisers come back only inside the token response (data.approval_advertisers, https://ad-market.xiaohongshu.com/docs-center?bizType=943&articleId=4808), and 获取代理商子账号列表 is limited to agency developers (账户服务 category).

## Credentials

- `PLATFORM_MCP_XIAOHONGSHU_PUGONGYING_CLIENT_ID` — app_id of the 小红书开放平台 聚光 (MAPI) application (应用中心 > 编辑应用).
- `PLATFORM_MCP_XIAOHONGSHU_PUGONGYING_CLIENT_SECRET` — secret of that application (应用中心 > 编辑应用); sent as `secret` in the refresh call.
- `PLATFORM_MCP_XIAOHONGSHU_PUGONGYING_REFRESH_TOKEN` — refresh_token from 获取token (auth_code exchange after the advertiser authorised the app's url). Valid 30 days and replaced on every refresh ('刷新后会生成新的 token，老的 access_token 和 refresh_token 将不可再使用'); set PLATFORM_MCP_STATE_DIR so the newest one survives restarts.
- `PLATFORM_MCP_XIAOHONGSHU_PUGONGYING_ADVERTISER_ID` — 聚光 广告主ID (advertiser_id; returned as approval_advertisers with the token); used by the probe, update_budget and pause_resume.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve xiaohongshu_pugongying   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve xiaohongshu_pugongying
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve xiaohongshu_pugongying   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/xiaohongshu_pugongying-mcp`. Python and TypeScript serve identical tools.
