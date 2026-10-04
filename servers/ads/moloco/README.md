# Moloco Ads MCP server

Category: **ads** · Docs: https://developer.moloco.cloud/docs/getting-started · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/moloco.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /ad-accounts` (https://developer.moloco.cloud/reference/dspapi_listadaccounts-1)
- `list_accounts` — `GET /ad-accounts` (https://developer.moloco.cloud/reference/dspapi_listadaccounts-1)
- `list_campaigns` — `GET /campaigns` (https://developer.moloco.cloud/reference/dspapi_listcampaigns-1)
- `get_report` — `POST /analytics-overview` (https://developer.moloco.cloud/reference/dspapi_queryanalyticsoverview)
- ~~`update_budget`~~ not offered: Budgets live in campaign.budget_schedule.daily_schedule.daily_budget as {currency, amount_micros} (amount × 1,000,000 as an int64 string) and are changed with PUT /cm/v1/campaigns/{campaign_id} taking the whole dspCampaign object (https://developer.moloco.cloud/reference/dspapi_updatecampaign-1); the runtime can neither scale daily_budget to micros nor send a read-modify-write of the full campaign.
- ~~`pause_resume`~~ not offered: Pausing sets campaign.enabling_state DISABLED/ENABLED (https://developer.moloco.cloud/docs/campaign-management-api), but the only write is PUT /cm/v1/campaigns/{campaign_id} with the whole dspCampaign object as body (https://developer.moloco.cloud/reference/dspapi_updatecampaign-1); partial updates are not documented, so a body with only enabling_state could reset other settings.

## Credentials

- `PLATFORM_MCP_MOLOCO_API_KEY` — Moloco Ads API key (Moloco Ads > account settings > API key; created for the ad account's workplace). Exchanged at POST https://api.moloco.cloud/cm/v1/auth/tokens {api_key} for a 16-hour bearer token, re-requested on expiry or 401.

## Run

    uvx platform-mcp-hub serve moloco          # Python
    npx -y platform-mcp-hub serve moloco       # TypeScript
    claude mcp add moloco -- uvx platform-mcp-hub serve moloco

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/moloco-mcp`. Python and TypeScript serve identical tools.
