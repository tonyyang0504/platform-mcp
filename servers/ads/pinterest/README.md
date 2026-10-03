# Pinterest Ads MCP server

Category: **ads** · Docs: https://developers.pinterest.com/docs/api/v5/ · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/pinterest.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /user_account` (https://developers.pinterest.com/docs/api/v5/user_account-get)
- `list_accounts` — `GET /ad_accounts` (https://developers.pinterest.com/docs/api/v5/ad_accounts-list)
- `list_campaigns` — `GET /ad_accounts/{account_id}/campaigns` (https://developers.pinterest.com/docs/api/v5/campaigns-list)
- `get_report` — `GET /ad_accounts/{account_id}/campaigns/analytics` (https://developers.pinterest.com/docs/api/v5/campaigns-analytics)
- `update_budget` — `PATCH /ad_accounts/{ad_account_id}/campaigns` (https://developers.pinterest.com/docs/api/v5/campaigns-update)
- `pause_resume` — `PATCH /ad_accounts/{ad_account_id}/campaigns` (https://developers.pinterest.com/docs/api/v5/campaigns-update)

## Credentials

- `PLATFORM_MCP_PINTEREST_CLIENT_ID` — Pinterest app id; HTTP Basic username on POST https://api.pinterest.com/v5/oauth/token.
- `PLATFORM_MCP_PINTEREST_CLIENT_SECRET` — Pinterest app secret key; HTTP Basic password on the token request.
- `PLATFORM_MCP_PINTEREST_REFRESH_TOKEN` — Refresh token (starts with `pinr`) from the authorization-code flow with scopes user_accounts:read, ads:read and ads:write. Continuous refresh tokens last 60 days and every refresh returns a new one: the runtime keeps the rotated token in memory, and when PLATFORM_MCP_STATE_DIR is set it saves it to <dir>/pinterest.json (mode 0600) and prefers it over this variable on the next start.
- `PLATFORM_MCP_PINTEREST_AD_ACCOUNT_ID` — Ad account id (digits) that update_budget and pause_resume PATCH (PATCH /v5/ad_accounts/{ad_account_id}/campaigns); those verbs take only a campaign id.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve ads/pinterest   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve ads/pinterest
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve ads/pinterest   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/pinterest-ads-mcp`. Python and TypeScript serve identical tools.
