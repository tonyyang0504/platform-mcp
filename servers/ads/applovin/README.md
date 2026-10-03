# AppLovin Ads (AXON) MCP server

Category: **ads** · Docs: https://support.applovin.com/en/growth/promoting-your-apps/api/reporting-api · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/applovin.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /campaign/list` (https://support.applovin.com/en/growth/promoting-your-apps/api/axon-campaign-management-api)
- `list_campaigns` — `GET /campaign/list` (https://support.applovin.com/en/growth/promoting-your-apps/api/axon-campaign-management-api)
- `get_report` — `GET https://r.applovin.com/report` (https://support.applovin.com/en/growth/promoting-your-apps/api/reporting-api)
- `update_budget` — `POST /campaign/update` (https://support.applovin.com/en/growth/promoting-your-apps/api/axon-campaign-management-api)
- `pause_resume` — `POST /campaign/update` (https://support.applovin.com/en/growth/promoting-your-apps/api/axon-campaign-management-api)
- ~~`list_accounts`~~ not offered: The Campaign Management API works on one account given as the account_id query parameter and has no account-listing endpoint (https://support.applovin.com/en/growth/promoting-your-apps/api/axon-campaign-management-api: 'You also must add the account_id query parameter to each request').

## Credentials

- `PLATFORM_MCP_APPLOVIN_CAMPAIGN_API_KEY` — Campaign Management API key (AppLovin dashboard > your account, top right > Keys; not the Ad Unit Management key), sent as the raw `Authorization` header value on api.ads.axon.ai.
- `PLATFORM_MCP_APPLOVIN_REPORT_KEY` — Report Key (dashboard > account > Keys), sent as the api_key query parameter of GET https://r.applovin.com/report; needed only for get_report.
- `PLATFORM_MCP_APPLOVIN_ACCOUNT_ID` — Numeric AppLovin account id (dashboard > account > Go to settings: the number after the account name); every Campaign Management call carries it as ?account_id=.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve applovin   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve applovin
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve applovin   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/applovin-mcp`. Python and TypeScript serve identical tools.
