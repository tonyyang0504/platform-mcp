# X Ads MCP server

Category: **ads** · Docs: https://docs.x.com/x-ads-api/introduction · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/x_ads.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /accounts` (https://docs.x.com/x-ads-api/campaign-management/reference#get-accounts)
- `list_accounts` — `GET /accounts` (https://docs.x.com/x-ads-api/campaign-management/reference#get-accounts)
- `list_campaigns` — `GET /accounts/{account_id}/campaigns` (https://docs.x.com/x-ads-api/campaign-management/reference#get-accounts-account-id-campaigns)
- `get_report` — `GET /stats/accounts/{account_id}` (https://docs.x.com/x-ads-api/analytics)
- `update_budget` — `PUT /accounts/{account_id}/campaigns/{campaign_id}` (https://docs.x.com/x-ads-api/campaign-management/reference#put-accounts-account-id-campaigns-campaign-id)
- `pause_resume` — `PUT /accounts/{account_id}/campaigns/{campaign_id}` (https://docs.x.com/x-ads-api/campaign-management/reference#put-accounts-account-id-campaigns-campaign-id)

## Credentials

- `PLATFORM_MCP_X_ADS_CONSUMER_KEY` — API Key (consumer key) of an X developer app approved for Ads API access (Ads API Access Form, https://docs.x.com/forms/ads-api-access).
- `PLATFORM_MCP_X_ADS_CONSUMER_SECRET` — API Key Secret (consumer secret) of the same app.
- `PLATFORM_MCP_X_ADS_ACCESS_TOKEN` — OAuth 1.0a user access token of an X user with access to the ads account (app management UI or the 3-legged OAuth flow).
- `PLATFORM_MCP_X_ADS_ACCESS_TOKEN_SECRET` — OAuth 1.0a access token secret belonging to that access token.
- `PLATFORM_MCP_X_ADS_ACCOUNT_ID` — Ads account id (e.g. 18ce54d4x5t) used by update_budget and pause_resume, whose inputs carry only the campaign id; list_accounts shows the ids.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve x_ads   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve x_ads
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve x_ads   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/x_ads-mcp`. Python and TypeScript serve identical tools.
