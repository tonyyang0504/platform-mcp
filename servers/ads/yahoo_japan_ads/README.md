# LINEヤフー広告 (formerly Yahoo! JAPAN Ads) MCP server

Category: **ads** · Docs: https://ads-developers.yahoo.co.jp/ja/ads-api/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/yahoo_japan_ads.json`; edit the catalog, not this file.

## Tools

- `me` — `POST /BaseAccountService/get` (https://github.com/yahoojp-marketing/ads-search-api-documents/tree/master/design/v20/baseaccount)
- `list_accounts` — `POST /BaseAccountService/get` (https://github.com/yahoojp-marketing/ads-search-api-documents/tree/master/design/v20/baseaccount)
- `list_campaigns` — `POST /CampaignService/get` (https://github.com/yahoojp-marketing/ads-search-api-documents/tree/master/design/v20/campaign)
- `update_budget` — `POST /CampaignService/set` (https://github.com/yahoojp-marketing/ads-search-api-documents/tree/master/design/v20/campaign)
- `pause_resume` — `POST /CampaignService/set` (https://github.com/yahoojp-marketing/ads-search-api-documents/tree/master/design/v20/campaign)
- ~~`get_report`~~ not offered: Search ads reports are asynchronous: ReportDefinitionService/add creates a job that is polled and then downloaded as a file (ReportDefinitionService/download, https://github.com/yahoojp-marketing/ads-search-api-documents/tree/master/design/v20/reportdefinition); the runtime has no report polling or file download.

## Credentials

- `PLATFORM_MCP_YAHOO_JAPAN_ADS_CLIENT_ID` — Client ID of your approved LINEヤフー広告 API application (API管理ツール).
- `PLATFORM_MCP_YAHOO_JAPAN_ADS_CLIENT_SECRET` — The application's client secret.
- `PLATFORM_MCP_YAHOO_JAPAN_ADS_REFRESH_TOKEN` — Refresh token from one authorization-code login with a Business ID (scope yahooads, https://ads-developers.yahoo.co.jp/ja/ads-api/startup-guide/api-call.html); valid until the user revokes the app. One-hour access tokens are minted from it.
- `PLATFORM_MCP_YAHOO_JAPAN_ADS_BASE_ACCOUNT_ID` — Account the Business ID directly holds rights on (MCC or ad account id from BaseAccountService/get), sent as the x-z-base-account-id header on every call.
- `PLATFORM_MCP_YAHOO_JAPAN_ADS_ACCOUNT_ID` — Search ad account id used by update_budget and pause_resume (CampaignService/set requires accountId in the body).

## Run

    uvx platform-mcp-hub serve yahoo_japan_ads          # Python
    npx -y platform-mcp-hub serve yahoo_japan_ads       # TypeScript
    claude mcp add yahoo_japan_ads -- uvx platform-mcp-hub serve yahoo_japan_ads

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/yahoo_japan_ads-mcp`. Python and TypeScript serve identical tools.
