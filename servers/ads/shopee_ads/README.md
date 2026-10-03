# Shopee Ads MCP server

Category: **ads** · Docs: https://open.shopee.com/documents/v2/v2.ads.get_total_balance?module=127&type=1 · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/shopee_ads.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /api/v2/ads/get_total_balance` (https://open.shopee.com/documents/v2/v2.ads.get_total_balance?module=127&type=1)
- `list_campaigns` — `GET /api/v2/ads/get_product_level_campaign_id_list` (https://open.shopee.com/documents/v2/v2.ads.get_product_level_campaign_id_list?module=127&type=1)
- `get_report` — `GET /api/v2/ads/get_all_cpc_ads_daily_performance` (https://open.shopee.com/documents/v2/v2.ads.get_all_cpc_ads_daily_performance?module=127&type=1)
- `update_budget` — `POST /api/v2/ads/edit_manual_product_ads` (https://open.shopee.com/documents/v2/v2.ads.edit_manual_product_ads?module=127&type=1)
- `pause_resume` — `POST /api/v2/ads/edit_manual_product_ads` (https://open.shopee.com/documents/v2/v2.ads.edit_manual_product_ads?module=127&type=1)
- ~~`list_accounts`~~ not offered: The Ads API is shop-scoped: every call carries one shop_id and the Ads module has no account listing (v2.ads.* list: get_total_balance, get_shop_toggle_info, performance, product campaign and GMS calls; https://open.shopee.com/documents/v2/v2.ads.get_total_balance?module=127&type=1).

## Credentials

- `PLATFORM_MCP_SHOPEE_ADS_PARTNER_KEY` — partner_key (live key) of the Shopee Open Platform app with the Ads (AMS/Ads) API permission; signs the token refresh and every shop call (HMAC-SHA256). Never sent on the wire.
- `PLATFORM_MCP_SHOPEE_ADS_REFRESH_TOKEN` — refresh_token from GetAccessToken (/api/v2/auth/token/get) after the shop authorised the app (https://open.shopee.com/developer-guide/20). Valid 30 days and rotated on every refresh; set PLATFORM_MCP_STATE_DIR so the newest one survives restarts.
- `PLATFORM_MCP_SHOPEE_ADS_PARTNER_ID` — partner_id of your Shopee Open Platform app (Console > App).
- `PLATFORM_MCP_SHOPEE_ADS_SHOP_ID` — shop_id of the authorised shop (returned in the authorisation redirect).

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve shopee_ads   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve shopee_ads
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve shopee_ads   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/shopee_ads-mcp`. Python and TypeScript serve identical tools.
