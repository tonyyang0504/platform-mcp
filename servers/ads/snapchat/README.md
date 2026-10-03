# Snapchat Ads (Snapchat Ads Manager) MCP server

Category: **ads** · Docs: https://developers.snap.com/api/marketing-api/Ads-API/introduction · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/snapchat.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /me` (https://developers.snap.com/api/marketing-api/Ads-API/user)
- `list_accounts` — `GET /organizations/{organization_id}/adaccounts` (https://developers.snap.com/api/marketing-api/Ads-API/ad-accounts)
- `list_campaigns` — `GET /adaccounts/{account_id}/campaigns` (https://developers.snap.com/api/marketing-api/Ads-API/campaigns)
- `get_report` — `GET /campaigns/{campaign_id}/stats` (https://developers.snap.com/api/marketing-api/Ads-API/measurement)
- `pause_resume` — `PATCH /adaccounts/{ad_account_id}/campaigns/{campaign_id}` (https://developers.snap.com/api/marketing-api/Ads-API/campaigns)
- ~~`update_budget`~~ not offered: Snap budgets are micro-currency integers ("daily_budget_micro: Daily Spend Cap (micro-currency)", minimum 20,000,000, https://developers.snap.com/api/marketing-api/Ads-API/campaigns); the adapter cannot scale a daily_budget into micros.

## Credentials

- `PLATFORM_MCP_SNAPCHAT_CLIENT_ID` — OAuth client id of your Snap Business Manager app (Business Details > OAuth apps).
- `PLATFORM_MCP_SNAPCHAT_CLIENT_SECRET` — The OAuth app's client secret (form body of the refresh request).
- `PLATFORM_MCP_SNAPCHAT_REFRESH_TOKEN` — Refresh token from one authorization-code consent with scope snapchat-marketing-api (https://developers.snap.com/api/marketing-api/Ads-API/authentication); 60-minute access tokens are minted from it.
- `PLATFORM_MCP_SNAPCHAT_ORGANIZATION_ID` — Snap organization id whose ad accounts list_accounts returns (GET /v1/me/organizations).
- `PLATFORM_MCP_SNAPCHAT_AD_ACCOUNT_ID` — Ad account id used by pause_resume (the campaign PATCH path is /v1/adaccounts/{ad_account_id}/campaigns/{campaign_id}).
- `PLATFORM_MCP_SNAPCHAT_TZ_OFFSET` — UTC offset of the ad account time zone, e.g. -07:00 or +01:00, used to build day-aligned start_time/end_time for get_report (Snap requires daily boundaries in the account time zone).

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve snapchat   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve snapchat
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve snapchat   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/snapchat-mcp`. Python and TypeScript serve identical tools.
