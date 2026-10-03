# Spotify Ads (Spotify Ads Manager) MCP server

Category: **ads** · Docs: https://developer.spotify.com/documentation/ads-api · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/spotify.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /businesses` (https://developer.spotify.com/documentation/ads-api/reference/v3.0/getBusinesses)
- `list_accounts` — `GET /businesses/{business_id}/ad_accounts` (https://developer.spotify.com/documentation/ads-api/reference/v3.0/getAdAccountsInBusiness)
- `list_campaigns` — `GET /ad_accounts/{account_id}/campaigns` (https://developer.spotify.com/documentation/ads-api/reference/v3.0/getCampaigns)
- `get_report` — `GET /ad_accounts/{account_id}/aggregate_reports` (https://developer.spotify.com/documentation/ads-api/reference/v3.0/getAggregateReport)
- `pause_resume` — `PATCH /ad_accounts/{ad_account_id}/campaigns/{campaign_id}` (https://developer.spotify.com/documentation/ads-api/reference/v3.0/updateCampaign)
- ~~`update_budget`~~ not offered: Spotify budgets are set per ad set in micros ("budget.micro_amount: Total budget for the ad set multiplied by x10 to the 6th power", https://developer.spotify.com/documentation/ads-api/reference/v3.0/updateAdSet); campaigns carry no budget and the adapter cannot scale to micros.

## Credentials

- `PLATFORM_MCP_SPOTIFY_CLIENT_ID` — Client ID of your Spotify for Developers app registered for the Ads API (the Ads API Terms must be accepted for it; allowlisting can take an hour).
- `PLATFORM_MCP_SPOTIFY_CLIENT_SECRET` — The app's client secret (HTTP Basic on https://accounts.spotify.com/api/token).
- `PLATFORM_MCP_SPOTIFY_REFRESH_TOKEN` — Refresh token from one authorization-code login with your Ads Manager account (https://developer.spotify.com/documentation/ads-api/quick-start); it does not expire. One-hour access tokens are minted from it.
- `PLATFORM_MCP_SPOTIFY_BUSINESS_ID` — Spotify Ads business id whose ad accounts list_accounts returns (GET /businesses lists yours).
- `PLATFORM_MCP_SPOTIFY_AD_ACCOUNT_ID` — Ad account id used by pause_resume (the campaign PATCH path is /ad_accounts/{ad_account_id}/campaigns/{campaign_id}).

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve spotify   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve spotify
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve spotify   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/spotify-mcp`. Python and TypeScript serve identical tools.
