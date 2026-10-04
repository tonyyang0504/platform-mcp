# Amazon Fire TV / Prime Video Streaming TV Ads MCP server

Category: **ads** · Docs: https://advertising.amazon.com/API/docs/en-us/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/amazon_fire_tv_ads.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /v2/profiles/{profile_id}` (https://advertising.amazon.com/API/docs/en-us/reference/profiles)
- `list_accounts` — `GET /v2/profiles` (https://advertising.amazon.com/API/docs/en-us/reference/profiles)
- `list_campaigns` — `POST /st/campaigns/list` (https://advertising.amazon.com/API/docs/en-us/sponsored-tv#tag/Campaigns/operation/ListSponsoredTvCampaigns)
- `update_budget` — `PUT /st/campaigns` (https://advertising.amazon.com/API/docs/en-us/sponsored-tv#tag/Campaigns/operation/UpdateSponsoredTvCampaigns)
- `pause_resume` — `PUT /st/campaigns` (https://advertising.amazon.com/API/docs/en-us/sponsored-tv#tag/Campaigns/operation/UpdateSponsoredTvCampaigns)
- ~~`get_report`~~ not offered: Amazon Ads reporting is asynchronous: "POST /reporting/reports" creates a report job that is polled with "GET /reporting/reports/{reportId}" and downloaded from a URL (Amazon Ads API Postman collection, https://github.com/amzn/ads-advanced-tools-docs, Reporting); the runtime has no report polling.

## Credentials

- `PLATFORM_MCP_AMAZON_FIRE_TV_ADS_CLIENT_ID` — Login with Amazon client id of the app approved for the Amazon Ads API; also sent as the Amazon-Advertising-API-ClientId header.
- `PLATFORM_MCP_AMAZON_FIRE_TV_ADS_CLIENT_SECRET` — The LWA client secret (form body of the refresh_token grant).
- `PLATFORM_MCP_AMAZON_FIRE_TV_ADS_REFRESH_TOKEN` — LWA refresh token from the advertiser's consent (scope advertising::campaign_management); the runtime mints hourly access tokens from it at https://api.amazon.com/auth/o2/token.
- `PLATFORM_MCP_AMAZON_FIRE_TV_ADS_API_HOST` — Regional Amazon Ads API host: advertising-api.amazon.com (North America), advertising-api-eu.amazon.com (Europe) or advertising-api-fe.amazon.com (Far East).
- `PLATFORM_MCP_AMAZON_FIRE_TV_ADS_PROFILE_ID` — Advertising profile id of the advertiser running Sponsored TV (from GET /v2/profiles), sent as the Amazon-Advertising-API-Scope header.

## Run

    uvx platform-mcp-hub serve amazon_fire_tv_ads          # Python
    npx -y platform-mcp-hub serve amazon_fire_tv_ads       # TypeScript
    claude mcp add amazon_fire_tv_ads -- uvx platform-mcp-hub serve amazon_fire_tv_ads

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/amazon_fire_tv_ads-mcp`. Python and TypeScript serve identical tools.
