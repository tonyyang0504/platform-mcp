# Taboola Realize (Taboola Ads) MCP server

Category: **ads** · Docs: https://developers.taboola.com/backstage-api/reference/welcome · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/taboola.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /backstage/api/1.0/users/current/account` (https://developers.taboola.com/backstage-api/reference/get-account-details)
- `list_accounts` — `GET /backstage/api/1.0/users/current/allowed-accounts` (https://developers.taboola.com/backstage-api/reference/get-allowed-accounts)
- `list_campaigns` — `GET /backstage/api/1.0/{account_id}/campaigns/` (https://developers.taboola.com/backstage-api/reference/get-all-campaigns)
- `get_report` — `GET /backstage/api/1.0/{account_id}/reports/campaign-summary/dimensions/campaign_day_breakdown` (https://developers.taboola.com/backstage-api/reference/campaign-summary-report)
- `update_budget` — `POST /backstage/api/1.0/{account_id}/campaigns/{campaign_id}` (https://developers.taboola.com/backstage-api/reference/update-a-campaign)
- ~~`pause_resume`~~ not offered: Taboola pauses a campaign by updating it with the boolean `is_active` ("To pause (or unpause) a campaign, update the campaign, and set is_active to false (or true)", https://developers.taboola.com/backstage-api/docs/pausing-campaigns); the adapter's map: expression yields strings, not JSON booleans, so it cannot send is_active safely.

## Credentials

- `PLATFORM_MCP_TABOOLA_CLIENT_ID` — Backstage API client_id provided by your Taboola account manager.
- `PLATFORM_MCP_TABOOLA_CLIENT_SECRET` — The matching client_secret; client-credentials tokens last 12 hours (no refresh token) and are re-requested automatically.
- `PLATFORM_MCP_TABOOLA_ACCOUNT_ID` — Taboola account_id (the string id, e.g. demo-advertiser, from list_accounts) used by update_budget and pause_resume, whose paths are /backstage/api/1.0/{account_id}/campaigns/{campaign_id}.

## Run

    uvx platform-mcp-hub serve taboola          # Python
    npx -y platform-mcp-hub serve taboola       # TypeScript
    claude mcp add taboola -- uvx platform-mcp-hub serve taboola

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/taboola-mcp`. Python and TypeScript serve identical tools.
