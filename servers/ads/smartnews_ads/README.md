# SmartNews Ads MCP server

Category: **ads** · Docs: https://ads.smartnews.com/developers/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/smartnews_ads.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /api/bm/v1/developer_apps/me/ad_accounts` (https://ads.smartnews.com/developers/#tag/developer-app)
- `list_accounts` — `GET /api/bm/v1/developer_apps/me/ad_accounts` (https://ads.smartnews.com/developers/#tag/developer-app)
- `list_campaigns` — `GET /api/ma/v3/ad_accounts/{account_id}/campaigns` (https://ads.smartnews.com/developers/#tag/campaign/operation/getCampaignsPaginated)
- `get_report` — `GET /api/ma/v3/ad_accounts/{account_id}/insights/campaigns` (https://ads.smartnews.com/developers/#tag/insights/operation/getInsightsV3)
- `pause_resume` — `PATCH /api/ma/v3/ad_accounts/{ad_account_id}/campaigns/{campaign_id}` (https://ads.smartnews.com/developers/#tag/campaign/operation/patchCampaignById)
- ~~`update_budget`~~ not offered: SmartNews budgets are micros ("daily_budget_amount_micro: The average budget per day in micros of the ad account currency base unit", PATCH /api/ma/v3/ad_accounts/{ad_account_id}/campaigns/{campaign_id}, https://ads.smartnews.com/developers/#tag/campaign/operation/patchCampaignById); the adapter cannot scale a daily_budget into micros.

## Credentials

- `PLATFORM_MCP_SMARTNEWS_ADS_CLIENT_ID` — Developer app id (numeric client id) of an approved SmartNews Ads developer application.
- `PLATFORM_MCP_SMARTNEWS_ADS_CLIENT_SECRET` — The developer app's client secret; access tokens (scope ads-manager) last 24 hours and are re-requested automatically.
- `PLATFORM_MCP_SMARTNEWS_ADS_AD_ACCOUNT_ID` — SmartNews ad account id used by pause_resume (the campaign PATCH path is /api/ma/v3/ad_accounts/{ad_account_id}/campaigns/{campaign_id}).

## Run

    uvx platform-mcp-hub serve smartnews_ads          # Python
    npx -y platform-mcp-hub serve smartnews_ads       # TypeScript
    claude mcp add smartnews_ads -- uvx platform-mcp-hub serve smartnews_ads

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/smartnews_ads-mcp`. Python and TypeScript serve identical tools.
