# LinkedIn Ads (Campaign Manager) MCP server

Category: **ads** · Docs: https://learn.microsoft.com/en-us/linkedin/marketing/ · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/linkedin.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /rest/adAccountUsers` (https://learn.microsoft.com/en-us/linkedin/marketing/integrations/ads/account-structure/create-and-manage-account-users)
- `list_accounts` — `GET /rest/adAccounts` (https://learn.microsoft.com/en-us/linkedin/marketing/integrations/ads/account-structure/create-and-manage-accounts)
- `list_campaigns` — `GET /rest/adAccounts/{account_id}/adCampaigns` (https://learn.microsoft.com/en-us/linkedin/marketing/integrations/ads/account-structure/create-and-manage-campaigns)
- `update_budget` — `POST /rest/adAccounts/{ad_account_id}/adCampaigns/{campaign_id}` (https://learn.microsoft.com/en-us/linkedin/marketing/integrations/ads/account-structure/create-and-manage-campaigns)
- `pause_resume` — `POST /rest/adAccounts/{ad_account_id}/adCampaigns/{campaign_id}` (https://learn.microsoft.com/en-us/linkedin/marketing/integrations/ads/account-structure/create-and-manage-campaigns)
- `get_report` — `GET /rest/adAnalytics?q=analytics&pivot=CAMPAIGN&timeGranularity=DAILY` (https://learn.microsoft.com/en-us/linkedin/marketing/integrations/ads-reporting/ads-reporting)

## Credentials

- `PLATFORM_MCP_LINKEDIN_CLIENT_ID` — Client id of a LinkedIn app with the Advertising API product (scopes r_ads, rw_ads).
- `PLATFORM_MCP_LINKEDIN_CLIENT_SECRET` — The app's client secret (form body of the refresh_token grant at https://www.linkedin.com/oauth/v2/accessToken).
- `PLATFORM_MCP_LINKEDIN_REFRESH_TOKEN` — Programmatic refresh token from the 3-legged flow (available to approved Marketing API partners; valid about one year). The runtime mints 60-day access tokens from it.
- `PLATFORM_MCP_LINKEDIN_AD_ACCOUNT_ID` — Sponsored ad account id (digits) that owns the campaigns update_budget and pause_resume change (POST /rest/adAccounts/{adAccountId}/adCampaigns/{campaignId}); those verbs take only a campaign id.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve ads/linkedin   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve ads/linkedin
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve ads/linkedin   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/linkedin-ads-mcp`. Python and TypeScript serve identical tools.
