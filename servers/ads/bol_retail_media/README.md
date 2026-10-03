# bol Retail Media (Sponsored Products) MCP server

Category: **ads** · Docs: https://api.bol.com/retailer/public/Retailer-API/v11/functional/advertising-api/aapi-overview.html · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/bol_retail_media.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /budget-management/budget-settings` (https://api.bol.com/advertiser/docs/redoc/sponsored-products/v11/budget-management.html)
- `list_campaigns` — `POST /campaign-management/campaigns/list` (https://api.bol.com/advertiser/docs/redoc/sponsored-products/v11/campaign-management.html)
- `get_report` — `GET /reporting/performance` (https://api.bol.com/advertiser/docs/redoc/sponsored-products/v11/reporting.html)
- ~~`list_accounts`~~ not offered: The JWT belongs to one retailer account; the Advertising API has no account list (https://api.bol.com/retailer/public/Retailer-API/v11/functional/advertising-api/aapi-overview.html: authorization 'uses the same method of authentication as the standard intermediary authorization flow').
- ~~`update_budget`~~ not offered: PUT /campaign-management/campaigns replaces campaigns: each item requires campaignId plus name, startDate, targetCountries, targetChannels, campaignType and state (UpdateCampaignsRequest, https://api.bol.com/advertiser/docs/redoc/sponsored-products/v11/campaign-management.html). Changing only dailyBudget would need a read-modify-write the runtime cannot do.
- ~~`pause_resume`~~ not offered: Same PUT /campaign-management/campaigns full-object update (state ENABLED|PAUSED alongside the required name, startDate, targetCountries, targetChannels, campaignType); no partial state endpoint (https://api.bol.com/advertiser/docs/redoc/sponsored-products/v11/campaign-management.html).

## Credentials

- `PLATFORM_MCP_BOL_RETAIL_MEDIA_CLIENT_ID` — Client id of bol API credentials with Advertising API access (seller dashboard > Settings > API settings, or intermediary authorization for agencies); exchanged at POST https://login.bol.com/token (grant_type=client_credentials, HTTP Basic) for a ~5-minute JWT.
- `PLATFORM_MCP_BOL_RETAIL_MEDIA_CLIENT_SECRET` — The matching client secret. The JWT is cached and re-requested before expiry (bol bans IPs that request a token per call).

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve bol_retail_media   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve bol_retail_media
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve bol_retail_media   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/bol_retail_media-mcp`. Python and TypeScript serve identical tools.
