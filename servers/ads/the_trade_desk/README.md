# The Trade Desk MCP server

Category: **ads** · Docs: https://open.thetradedesk.com/advertiser/docsApp/AdvertiserReferences/api/ref/post-campaign-query-advertiser · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/the_trade_desk.json`; edit the catalog, not this file.

## Tools

- `me` — `POST /partner/query` (https://open.thetradedesk.com/advertiser/docsApp/AdvertiserReferences/api/ref/post-partner-query)
- `list_accounts` — `POST /advertiser/query/partner` (https://open.thetradedesk.com/advertiser/docsApp/AdvertiserReferences/api/ref/post-advertiser-query-partner)
- `list_campaigns` — `POST /campaign/query/advertiser` (https://open.thetradedesk.com/advertiser/docsApp/AdvertiserReferences/api/ref/post-campaign-query-advertiser)
- `update_budget` — `PUT /campaign` (https://open.thetradedesk.com/advertiser/docsApp/AdvertiserReferences/api/ref/put-campaign)
- ~~`get_report`~~ not offered: Date-ranged performance metrics are served by the GraphQL API ('generalReporting(where: { date: { gte: "2025-02-01", lt: "2025-03-01" } })', https://open.thetradedesk.com/advertiser/docsApp/GuidesAdvertiser/api/doc/AdvertiserGQLQueryExamples) whose selection-set braces the adapter's string templates cannot build, or by asynchronous My Reports schedules; the only REST metrics call, GET /v3/campaign/{campaignId}/metrics, returns 'Metrics and goals over the 4 week span' and cannot honour date_from/date_to.
- ~~`pause_resume`~~ not offered: Campaigns have no paused state in the Platform API: Availability is only 'Available' or 'Archived' and 'Once a campaign is updated to `Archived`, it cannot be set back to `Available`' (PUT /v3/campaign, https://open.thetradedesk.com/advertiser/docsApp/AdvertiserReferences/api/ref/put-campaign); delivery is switched on and off per ad group (isEnabled), which the campaign-level verb cannot address.

## Credentials

- `PLATFORM_MCP_THE_TRADE_DESK_API_TOKEN` — Platform API token generated in OpenTTD > Access Management > Generate Token / Key (Application: Platform API; lifetime one week to one year), sent as the TTD-Auth header. Short-lived tokens from POST /v3/authentication also work until they expire.
- `PLATFORM_MCP_THE_TRADE_DESK_PARTNER_ID` — Your Partner ID (e.g. from POST /v3/partner/query); list_accounts lists the advertisers of this partner (POST /v3/advertiser/query/partner needs PartnerId).

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve the_trade_desk   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve the_trade_desk
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve the_trade_desk   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/the_trade_desk-mcp`. Python and TypeScript serve identical tools.
