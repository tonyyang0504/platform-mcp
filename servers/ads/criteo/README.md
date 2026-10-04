# Criteo (Commerce Growth / Criteo GO) MCP server

Category: **ads** · Docs: https://developers.criteo.com/ · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/criteo.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /2026-07/advertisers/me` (https://developers.criteo.com/marketing-solutions/v2026.07/reference/advertiser/2026-07advertisersme)
- `list_accounts` — `GET /2026-07/advertisers/me` (https://developers.criteo.com/marketing-solutions/v2026.07/reference/advertiser/2026-07advertisersme)
- `list_campaigns` — `POST /2026-07/marketing-solutions/campaigns/search` (https://developers.criteo.com/marketing-solutions/v2026.07/reference/campaign/2026-07marketing-solutionscampaignssearch)
- `get_report` — `POST /2026-07/statistics/report` (https://developers.criteo.com/marketing-solutions/v2026.07/reference/analytics/2026-07statisticsreport)
- `update_budget` — `PATCH /2026-07/marketing-solutions/campaigns` (https://developers.criteo.com/marketing-solutions/v2026.07/reference/campaign/2026-07marketing-solutionscampaigns-1)
- ~~`pause_resume`~~ not offered: Criteo campaigns have no status: delivery is started and stopped per ad set (POST /2026-07/marketing-solutions/ad-sets/start and /ad-sets/stop with {data: [{id, type: AdSet}]}, https://developers.criteo.com/marketing-solutions/v2026.07/reference/campaign/2026-07marketing-solutionsad-setsstop), and PatchCampaign has only spendLimit/budgetAutomation/scheduledSpendLimit attributes; there is no campaign-level call.

## Credentials

- `PLATFORM_MCP_CRITEO_CLIENT_ID` — Client id of a Criteo Marketing Solutions app (Developer portal > app > Create new key), sent in the form body of POST https://api.criteo.com/oauth2/token (grant_type=client_credentials).
- `PLATFORM_MCP_CRITEO_CLIENT_SECRET` — The app key's secret. Tokens last 900 seconds and are re-requested automatically; the advertisers must have approved the app's consent.
- `PLATFORM_MCP_CRITEO_CURRENCY` — ISO 4217 currency for get_report (the statistics endpoint requires `currency`), e.g. EUR or USD.

## Run

    uvx platform-mcp-hub serve criteo          # Python
    npx -y platform-mcp-hub serve criteo       # TypeScript
    claude mcp add criteo -- uvx platform-mcp-hub serve criteo

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/criteo-mcp`. Python and TypeScript serve identical tools.
