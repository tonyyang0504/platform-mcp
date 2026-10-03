# Nextdoor Ads MCP server

Category: **ads** · Docs: https://developer.nextdoor.com/reference · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/nextdoor.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /api/v3/me` (https://developer.nextdoor.com/reference/get_api-v3-me)
- `list_accounts` — `GET /api/v3/me` (https://developer.nextdoor.com/reference/get_api-v3-me)
- `list_campaigns` — `GET /api/v3/advertisers/{account_id}/campaigns` (https://developer.nextdoor.com/reference/get_api-v3-advertisers-advertiserid-campaigns)
- `pause_resume` — `PUT /api/v3/advertisers/{advertiser_id}/campaigns/{campaign_id}/status` (https://developer.nextdoor.com/reference/put_api-v3-advertisers-advertiserid-campaigns-campaignid-status)
- ~~`get_report`~~ not offered: Synchronous stats ("GET /api/v3/advertisers/{advertiserId}/stats" and ".../campaigns/{campaignId}/stats", https://developer.nextdoor.com/reference/get_api-v3-advertisers-advertiserid-stats) return a single totals object rather than rows, which the adapter's list mapping cannot wrap; row reports ("POST /api/v3/advertisers/{advertiserId}/reports") are generated asynchronously.
- ~~`update_budget`~~ not offered: Nextdoor budgets are set on ad groups ("PUT /api/v3/advertisers/{advertiserId}/adgroups/{adGroupId}", https://developer.nextdoor.com/reference/put_api-v3-advertisers-advertiserid-adgroups-adgroupid); campaigns carry no budget field.

## Credentials

- `PLATFORM_MCP_NEXTDOOR_API_TOKEN` — Nextdoor Ads Manager API token (NAM > settings > API, https://ads.nextdoor.com/v2/manage/api) for an account granted Ads API access; one token per user, valid for one year, acting for every advertiser tied to the NAM account.
- `PLATFORM_MCP_NEXTDOOR_ADVERTISER_ID` — Nextdoor advertiser id used by pause_resume (the status path is /api/v3/advertisers/{advertiserId}/campaigns/{campaignId}/status).

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve ads/nextdoor   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve ads/nextdoor
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve ads/nextdoor   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/nextdoor-ads-mcp`. Python and TypeScript serve identical tools.
