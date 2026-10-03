# 네이버 검색광고 Naver Search Ads MCP server

Category: **ads** · Docs: https://naver.github.io/searchad-apidoc/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/naver_search_ads.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /billing/bizmoney` (https://naver.github.io/searchad-apidoc/#/tags/Bizmoney)
- `list_campaigns` — `GET /ncc/campaigns` (https://naver.github.io/searchad-apidoc/#/tags/Campaign)
- `get_report` — `GET /stats` (https://naver.github.io/searchad-apidoc/#/tags/Stat)
- `update_budget` — `PUT /ncc/campaigns/{campaign_id}` (https://naver.github.io/searchad-apidoc/#/tags/Campaign)
- `pause_resume` — `PUT /ncc/campaigns/{campaign_id}` (https://naver.github.io/searchad-apidoc/#/tags/Campaign)
- ~~`list_accounts`~~ not offered: Requests are made for one advertiser selected by X-Customer; linked client accounts (GET /customer-links?type=MYCLIENTS, used in Naver's sample code) are an agency feature whose response fields the reference does not document (https://naver.github.io/searchad-apidoc/).

## Credentials

- `PLATFORM_MCP_NAVER_SEARCH_ADS_API_KEY` — API license (access license) from NAVER Search Advertiser's Center > Tools > API Manager, sent as X-API-KEY.
- `PLATFORM_MCP_NAVER_SEARCH_ADS_SECRET_KEY` — The license's secret key; signs every request: X-Signature = base64(HMAC-SHA256(secret, "<X-Timestamp ms>.<METHOD>.<path>")).
- `PLATFORM_MCP_NAVER_SEARCH_ADS_CUSTOMER_ID` — Numeric advertiser customer id (shown in the Search Advertiser's Center), sent as X-Customer and as customerId in campaign updates.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve naver_search_ads   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve naver_search_ads
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve naver_search_ads   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/naver_search_ads-mcp`. Python and TypeScript serve identical tools.
