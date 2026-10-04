# DoorDash Ads MCP server

Category: **ads** · Docs: https://developer.doordash.com/en-US/api/ads/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/doordash_ads.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /ads/api/v1/{campaign_type}/campaigns` (https://developer.doordash.com/en-US/api/ads/#tag/Campaigns/operation/getCampaigns)
- `list_campaigns` — `GET /ads/api/v1/{campaign_type}/campaigns` (https://developer.doordash.com/en-US/api/ads/#tag/Campaigns/operation/getCampaigns)
- `update_budget` — `PUT /ads/api/v1/{campaign_type}/campaigns` (https://developer.doordash.com/en-US/api/ads/#tag/Campaigns/operation/updateCampaign)
- `pause_resume` — `PUT /ads/api/v1/{campaign_type}/campaigns` (https://developer.doordash.com/en-US/api/ads/#tag/Campaigns/operation/updateCampaign)
- ~~`list_accounts`~~ not offered: No account-listing operation exists in the Ads API (tags: Campaigns, Ad Groups, Product Ads, Assets, Creatives (SB), Merchants (Retailers), Keywords (SP), Resources, Catalog, Report, Menu, Targeting; https://developer.doordash.com/en-US/api/ads/); the API key is scoped to the advertiser.
- ~~`get_report`~~ not offered: Reports are asynchronous files: 'Create report' (POST /ads/api/v1/sp/reports/{recordType}/create) returns only a reportId, and 'Download report' (GET /ads/api/v1/sp/reports/download/{reportId}) returns a status and a download url to an S3 file (https://developer.doordash.com/en-US/api/ads/#tag/Report), not metric rows.

## Credentials

- `PLATFORM_MCP_DOORDASH_ADS_API_KEY` — DoorDash Ads API key; the Ads API reference's security scheme 'Ads API Key Authentication' reads: 'We will be using stateful token based API keys to authenticate clients, passed in the Authorization header as Bearer {API_KEY}' (https://developer.doordash.com/en-US/redocusaurus/plugin-redoc-11.yaml). Issued to onboarded DoorDash Ads (CPG) advertisers and partners.
- `PLATFORM_MCP_DOORDASH_ADS_CAMPAIGN_TYPE` — Campaign type path segment of every campaign call: 'sp' (Sponsored Products) or 'sb' (Sponsored Brand).

## Run

    uvx platform-mcp-hub serve doordash_ads          # Python
    npx -y platform-mcp-hub serve doordash_ads       # TypeScript
    claude mcp add doordash_ads -- uvx platform-mcp-hub serve doordash_ads

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/doordash_ads-mcp`. Python and TypeScript serve identical tools.
