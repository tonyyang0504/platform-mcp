# 百度营销 Baidu Marketing MCP server

Category: **ads** · Docs: https://dev2.baidu.com/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/baidu_marketing.json`; edit the catalog, not this file.

## Tools

- `me` — `POST /AccountService/getAccountInfo` (https://dev2.baidu.com/content?sceneType=0&pageId=100256&nodeId=63)
- `list_accounts` — `POST https://api.baidu.com/json/feed/v1/MccFeedService/getUserListByMccid` (https://dev2.baidu.com/content?sceneType=0&pageId=100182&nodeId=13)
- `list_campaigns` — `POST /CampaignService/getCampaign` (https://dev2.baidu.com/content?sceneType=0&pageId=100260&nodeId=198)
- `get_report` — `POST /OpenApiReportService/getReportData` (https://dev2.baidu.com/content?sceneType=0&pageId=102474&nodeId=698)
- `update_budget` — `POST /CampaignService/updateCampaign` (https://dev2.baidu.com/content?sceneType=0&pageId=100262&nodeId=200)
- `pause_resume` — `POST /CampaignService/updateCampaign` (https://dev2.baidu.com/content?sceneType=0&pageId=100262&nodeId=200)

## Credentials

- `PLATFORM_MCP_BAIDU_MARKETING_CLIENT_ID` — Your application's appId (商业开发者中心 → 应用管理 → 应用详情).
- `PLATFORM_MCP_BAIDU_MARKETING_CLIENT_SECRET` — The application's secretKey (shown in the approved application's details).
- `PLATFORM_MCP_BAIDU_MARKETING_REFRESH_TOKEN` — refreshToken from exchanging the authorization code once at POST https://u.baidu.com/oauth/accessToken (valid 30 days; each refresh returns a new one, saved when PLATFORM_MCP_STATE_DIR is set).
- `PLATFORM_MCP_BAIDU_MARKETING_USER_ID` — userId of the promotion account that authorized the app (returned by the OAuth callback / accessToken exchange).
- `PLATFORM_MCP_BAIDU_MARKETING_USER_NAME` — 推广账户名称 (userName) of the account to operate — sent as header.userName; with a super-admin (超管) authorization this may be any sub-account.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve baidu_marketing   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve baidu_marketing
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve baidu_marketing   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/baidu_marketing-mcp`. Python and TypeScript serve identical tools.
