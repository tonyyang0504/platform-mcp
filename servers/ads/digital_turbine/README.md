# Digital Turbine (DT Ads) MCP server

Category: **ads** · Docs: https://docs.digitalturbine.com/offerwall-advertisers/advertiser-management-api · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/digital_turbine.json`; edit the catalog, not this file.

## Tools

- `update_budget` — `POST /graphql` (https://docs.digitalturbine.com/offerwall-advertisers/advertiser-management-api)
- `pause_resume` — `POST /graphql` (https://docs.digitalturbine.com/offerwall-advertisers/advertiser-management-api)
- ~~`me`~~ not offered: The Management API documents only the offerCampaignBulkUpdateBids mutation and a single-offer offerCampaign query that needs an offer id (https://docs.digitalturbine.com/offerwall-advertisers/advertiser-management-api); there is no account or viewer query to probe.
- ~~`list_accounts`~~ not offered: The token 'identifies the advertiser account'; no account listing is documented (https://docs.digitalturbine.com/offerwall-advertisers/advertiser-management-api).
- ~~`list_campaigns`~~ not offered: Only a single-offer query (offerCampaign by id or cmsId) is documented; there is no offer list query (https://docs.digitalturbine.com/offerwall-advertisers/advertiser-management-api).
- ~~`get_report`~~ not offered: The Offerwall Reporting API is asynchronous: POST https://reporting.fyber.com/api/v1/report/offerwall?format=csv returns a URL 'to be polled (GET request) until the body response (file) is populated' within up to an hour, as CSV, with a separate client-credentials token (https://docs.digitalturbine.com/offerwall-advertisers/reporting/reporting-api).

## Credentials

- `PLATFORM_MCP_DIGITAL_TURBINE_MANAGEMENT_API_TOKEN` — Offerwall Advertiser Management API token (ACP Edge Console > Account > Security Tokens > Add Token > Management API Token; shown once), sent as the x-api-key header. It identifies the advertiser account.

## Run

    uvx platform-mcp-hub serve digital_turbine          # Python
    npx -y platform-mcp-hub serve digital_turbine       # TypeScript
    claude mcp add digital_turbine -- uvx platform-mcp-hub serve digital_turbine

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/digital_turbine-mcp`. Python and TypeScript serve identical tools.
