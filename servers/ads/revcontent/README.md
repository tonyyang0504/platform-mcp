# Revcontent MCP server

Category: **ads** · Docs: https://api.revcontent.io/docs/stats/index.html · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/revcontent.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /stats/api/v1.0/boosts` (https://api.revcontent.io/docs/stats/index.html#api-Campaigns-GetAllBoosts)
- `list_accounts` — `GET /stats/api/v1.0/sub_accounts/list_accounts` (https://api.revcontent.io/docs/stats/index.html#api-Sub_Accounts-ListAccounts)
- `list_campaigns` — `GET /stats/api/v1.0/boosts` (https://api.revcontent.io/docs/stats/index.html#api-Campaigns-GetAllBoosts)
- `get_report` — `GET /stats/api/v1.0/boosts/performance` (https://api.revcontent.io/docs/stats/index.html#api-Campaigns-GetBoostPerformance)
- `update_budget` — `POST /stats/api/v1.0/boosts/{campaign_id}/settings` (https://api.revcontent.io/docs/stats/index.html#api-Campaigns-PostBoostSettings)
- `pause_resume` — `POST /stats/api/v1.0/boosts` (https://api.revcontent.io/docs/stats/index.html#api-Campaigns-PostBoostsStatus)

## Credentials

- `PLATFORM_MCP_REVCONTENT_CLIENT_ID` — client_id under Account Settings > 'Stats API Credentials' (API access is enabled by your Revcontent representative).
- `PLATFORM_MCP_REVCONTENT_CLIENT_SECRET` — client_secret from the same section; access tokens last 24 hours and are re-requested automatically.

## Run

    uvx platform-mcp-hub serve revcontent          # Python
    npx -y platform-mcp-hub serve revcontent       # TypeScript
    claude mcp add revcontent -- uvx platform-mcp-hub serve revcontent

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/revcontent-mcp`. Python and TypeScript serve identical tools.
