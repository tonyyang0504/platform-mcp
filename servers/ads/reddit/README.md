# Reddit Ads MCP server

Category: **ads** · Docs: https://ads-api.reddit.com/docs/v3/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/reddit.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /me` (https://ads-api.reddit.com/docs/v3/api/reddit-advertising-api)
- `list_accounts` — `GET /businesses/{business_id}/ad_accounts` (https://ads-api.reddit.com/docs/v3/api/ad-accounts)
- `list_campaigns` — `GET /ad_accounts/{account_id}/campaigns` (https://ads-api.reddit.com/docs/v3/api/campaigns)
- `get_report` — `POST /ad_accounts/{account_id}/reports` (https://ads-api.reddit.com/docs/v3/api/get-a-report)
- `pause_resume` — `PATCH /campaigns/{campaign_id}` (https://ads-api.reddit.com/docs/v3/api/campaigns)
- ~~`update_budget`~~ not offered: Reddit campaign budgets are microcurrency integers ("goal_value: Campaign-level goal value (microcurrency). Only works when is_campaign_budget_optimization is true", PATCH /api/v3/campaigns/{campaign_id}, https://ads-api.reddit.com/docs/v3/api/campaigns); the adapter cannot scale a daily_budget to micros, and non-CBO budgets live on ad groups.

## Credentials

- `PLATFORM_MCP_REDDIT_CLIENT_ID` — App ID of your Reddit Ads developer application (business > developer applications), sent as HTTP Basic user on the token call.
- `PLATFORM_MCP_REDDIT_CLIENT_SECRET` — The developer application's secret (HTTP Basic password on https://www.reddit.com/api/v1/access_token).
- `PLATFORM_MCP_REDDIT_REFRESH_TOKEN` — Refresh token from one authorization-code consent with duration=permanent and scope adsread,adsedit (https://ads-api.reddit.com/docs/v3/guides/quick-start/authenticate); access tokens last one hour or one day and are re-minted from it.
- `PLATFORM_MCP_REDDIT_BUSINESS_ID` — Reddit business id whose ad accounts list_accounts returns (GET /me/businesses lists yours).

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve ads/reddit   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve ads/reddit
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve ads/reddit   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/reddit-ads-mcp`. Python and TypeScript serve identical tools.
