# Avito Advertising (Авито Реклама) MCP server

Category: **ads** · Docs: https://ads-help.avito.com/external/api · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/avito_ads.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /v1/account/{account_id}` (https://github.com/avito-tech/avito-ads-sdk-python3/blob/HEAD/avito_ads/_core/operations.py)
- `list_accounts` — `GET /v1/account/{account_id}/children` (https://github.com/avito-tech/avito-ads-sdk-python3/blob/HEAD/avito_ads/_core/operations.py)
- `list_campaigns` — `POST /v1/account/{account_id}/campaigns` (https://github.com/avito-tech/avito-ads-sdk-python3/blob/HEAD/avito_ads/_core/operations.py)
- `get_report` — `POST /v1/account/{account_id}/campaigns/{campaign_id}/stats` (https://github.com/avito-tech/avito-ads-sdk-python3/blob/HEAD/avito_ads/_core/operations.py)
- ~~`update_budget`~~ not offered: Budgets are set per creative group, not per campaign: POST /ads/v1/account/{account_id}/group/{group_id}/change-budget {budget} (https://github.com/avito-tech/avito-ads-sdk-python3/blob/HEAD/avito_ads/_core/operations.py, change_group_budget); the API has no campaign-budget call.
- ~~`pause_resume`~~ not offered: No status-change endpoint: the API lists campaigns/groups/creatives and changes group bids and budgets only ('Изменять ставку и бюджет группы', https://ads-help.avito.com/external/api).

## Credentials

- `PLATFORM_MCP_AVITO_ADS_CLIENT_ID` — Client Key created by an Admin in the Avito Advertising cabinet settings (API keys); exchanged at POST https://api.avito.ru/token (grant_type=client_credentials, form body) for a bearer token.
- `PLATFORM_MCP_AVITO_ADS_CLIENT_SECRET` — The matching Client Secret. Tokens are re-requested automatically on expiry or 401.
- `PLATFORM_MCP_AVITO_ADS_ACCOUNT_ID` — Numeric Avito Advertising account id (every path is /ads/v1/account/{account_id}/…); used by `me`.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve avito_ads   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve avito_ads
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve avito_ads   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/avito_ads-mcp`. Python and TypeScript serve identical tools.
