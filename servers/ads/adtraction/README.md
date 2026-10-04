# Adtraction MCP server

Category: **ads** · Docs: https://apidocs.adtraction.net/nextgen/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/adtraction.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /advertiser/account/` (https://apidocs.adtraction.net/nextgen/#v2-advertiser-account-get)
- `get_report` — `POST /advertiser/statistics/days/` (https://apidocs.adtraction.net/nextgen/#v2-advertiser-statistics-by-day-post)
- ~~`list_accounts`~~ not offered: The token belongs to one advertiser program; GET /v2/advertiser/account/ returns that single record (served as `me`) and there is no list endpoint (https://apidocs.adtraction.net/nextgen/#v2-advertiser-account-get).
- ~~`list_campaigns`~~ not offered: Adtraction is an affiliate network: the advertiser API lists channels, clicks, transactions, segments and statistics but has no campaign resource (https://apidocs.adtraction.net/nextgen/, Advertiser section).
- ~~`update_budget`~~ not offered: No budget endpoint: 'Advertiser' covers account, channels, clicks, transactions, segments, coupons and statistics only (https://apidocs.adtraction.net/nextgen/); commissions are paid per transaction.
- ~~`pause_resume`~~ not offered: No campaign or program status endpoint in the Advertiser API (https://apidocs.adtraction.net/nextgen/); only channel approval status (PUT /advertiser/channels/, deprecated).

## Credentials

- `PLATFORM_MCP_ADTRACTION_API_TOKEN` — Adtraction advertiser API token (log in to Adtraction > Account > Settings), sent as the X-Token header; it determines the advertiser program the calls see.

## Run

    uvx platform-mcp-hub serve adtraction          # Python
    npx -y platform-mcp-hub serve adtraction       # TypeScript
    claude mcp add adtraction -- uvx platform-mcp-hub serve adtraction

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/adtraction-mcp`. Python and TypeScript serve identical tools.
