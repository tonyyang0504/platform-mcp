# Google Display & Video 360 MCP server

Category: **ads** · Docs: https://developers.google.com/display-video/api/guides/getting-started/overview · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/dv360.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /v4/partners` (https://developers.google.com/display-video/api/reference/rest/v4/partners/list)
- `list_accounts` — `GET /v4/advertisers` (https://developers.google.com/display-video/api/reference/rest/v4/advertisers/list)
- `list_campaigns` — `GET /v4/advertisers/{account_id}/campaigns` (https://developers.google.com/display-video/api/reference/rest/v4/advertisers.campaigns/list)
- `pause_resume` — `PATCH /v4/advertisers/{advertiser_id}/campaigns/{campaign_id}` (https://developers.google.com/display-video/api/reference/rest/v4/advertisers.campaigns/patch)
- ~~`get_report`~~ not offered: DV360 reporting runs through the Bid Manager API as asynchronous queries (create a query, run it, poll the report and download a CSV file; https://developers.google.com/bid-manager/guides/get-started/overview); the runtime has no report polling or CSV download.
- ~~`update_budget`~~ not offered: DV360 campaign budgets are planned amounts over a date range (campaignBudgets[].budgetAmountMicros, https://developers.google.com/display-video/api/reference/rest/v4/advertisers.campaigns); spend is paced on insertion orders and line items, and there is no campaign daily budget.

## Credentials

- `PLATFORM_MCP_DV360_CLIENT_ID` — OAuth 2.0 client id of a Google Cloud project with the Display & Video 360 API enabled.
- `PLATFORM_MCP_DV360_CLIENT_SECRET` — The OAuth client's secret (form body of the refresh_token grant).
- `PLATFORM_MCP_DV360_REFRESH_TOKEN` — Refresh token from Google's consent flow with scope https://www.googleapis.com/auth/display-video, for a user with a DV360 user profile (Admin/Standard for writes).
- `PLATFORM_MCP_DV360_PARTNER_ID` — DV360 partner id whose advertisers list_accounts returns (GET /v4/advertisers requires partnerId).
- `PLATFORM_MCP_DV360_ADVERTISER_ID` — DV360 advertiser id used by pause_resume (the campaign PATCH path is /v4/advertisers/{advertiserId}/campaigns/{campaignId}).

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve dv360   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve dv360
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve dv360   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/dv360-mcp`. Python and TypeScript serve identical tools.
