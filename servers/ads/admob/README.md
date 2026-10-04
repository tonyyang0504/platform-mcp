# Google AdMob MCP server

Category: **ads** · Docs: https://developers.google.com/admob/api · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/admob.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /v1/accounts` (https://developers.google.com/admob/api/reference/rest/v1/accounts/list)
- `list_accounts` — `GET /v1/accounts` (https://developers.google.com/admob/api/reference/rest/v1/accounts/list)
- `get_report` — `POST /v1/accounts/{account_id}/networkReport:generate` (https://developers.google.com/admob/api/reference/rest/v1/accounts.networkReport/generate)
- ~~`list_campaigns`~~ not offered: AdMob is a publisher monetisation API; its v1 surface is accounts, networkReport and mediationReport only ("The AdMob API allows publishers to programmatically get information about their AdMob account", https://developers.google.com/admob/api/reference/rest). There are no advertiser campaigns.
- ~~`update_budget`~~ not offered: No campaigns or budgets exist in the AdMob API (https://developers.google.com/admob/api/reference/rest).
- ~~`pause_resume`~~ not offered: No campaigns exist in the AdMob API (https://developers.google.com/admob/api/reference/rest).

## Credentials

- `PLATFORM_MCP_ADMOB_CLIENT_ID` — OAuth 2.0 client id (Google Cloud console > Credentials) of a project with the AdMob API enabled.
- `PLATFORM_MCP_ADMOB_CLIENT_SECRET` — The OAuth client's secret, sent in the form body of the refresh_token grant.
- `PLATFORM_MCP_ADMOB_REFRESH_TOKEN` — Refresh token from Google's consent flow (offline access) with scope https://www.googleapis.com/auth/admob.readonly (or admob.report); the runtime mints hourly access tokens from it.

## Run

    uvx platform-mcp-hub serve admob          # Python
    npx -y platform-mcp-hub serve admob       # TypeScript
    claude mcp add admob -- uvx platform-mcp-hub serve admob

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/admob-mcp`. Python and TypeScript serve identical tools.
