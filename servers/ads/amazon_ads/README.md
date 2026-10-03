# Amazon Ads (Sponsored Products / Brands / Display) MCP server

Category: **ads** · Docs: https://advertising.amazon.com/API/docs/en-us/ · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/amazon_ads.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /v2/profiles/{profile_id}` (https://advertising.amazon.com/API/docs/en-us/reference/profiles)
- `list_accounts` — `GET /v2/profiles` (https://advertising.amazon.com/API/docs/en-us/reference/profiles)
- `list_campaigns` — `POST /sp/campaigns/list` (https://advertising.amazon.com/API/docs/en-us/sponsored-products/3-0/openapi/prod#tag/Campaigns/operation/ListSponsoredProductsCampaigns)
- `update_budget` — `PUT /sp/campaigns` (https://advertising.amazon.com/API/docs/en-us/sponsored-products/3-0/openapi/prod#tag/Campaigns/operation/UpdateSponsoredProductsCampaigns)
- `pause_resume` — `PUT /sp/campaigns` (https://advertising.amazon.com/API/docs/en-us/sponsored-products/3-0/openapi/prod#tag/Campaigns/operation/UpdateSponsoredProductsCampaigns)
- ~~`get_report`~~ not offered: Reporting v3 is asynchronous: POST /reporting/reports creates a report, GET /reporting/reports/{reportId} is polled until COMPLETED, and the rows are a gzipped JSON file at a pre-signed URL; the runtime makes one call per tool.

## Credentials

- `PLATFORM_MCP_AMAZON_ADS_CLIENT_ID` — Login with Amazon client id of the app approved for the Amazon Ads API; also sent as the Amazon-Advertising-API-ClientId header.
- `PLATFORM_MCP_AMAZON_ADS_CLIENT_SECRET` — The LWA client secret (form body of the refresh_token grant).
- `PLATFORM_MCP_AMAZON_ADS_REFRESH_TOKEN` — LWA refresh token from the advertiser's consent (scope advertising::campaign_management); the runtime mints hourly access tokens from it at https://api.amazon.com/auth/o2/token.
- `PLATFORM_MCP_AMAZON_ADS_API_HOST` — Regional Amazon Ads API host: advertising-api.amazon.com (North America), advertising-api-eu.amazon.com (Europe) or advertising-api-fe.amazon.com (Far East).
- `PLATFORM_MCP_AMAZON_ADS_PROFILE_ID` — Advertising profile id (one per advertiser and marketplace, from GET /v2/profiles), sent as the Amazon-Advertising-API-Scope header.
- `PLATFORM_MCP_AMAZON_ADS_ENV` — Vendor environment (default production): sandbox = production host with test accounts or test keys. Credentials are the environment's own; see adapter.environments in the catalog entry.
- `PLATFORM_MCP_AMAZON_ADS_BASE_URL` — Optional https base URL override (a mock or a private gateway); replaces the selected environment's base_url. Never echoed in errors.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve amazon_ads   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve amazon_ads
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve amazon_ads   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/amazon_ads-mcp`. Python and TypeScript serve identical tools.
