# Outbrain Amplify MCP server

Category: **ads** · Docs: https://developer.outbrain.com/home-page/amplify-api/documentation/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/outbrain.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /marketers` (https://amplifyv01.docs.apiary.io/#reference/marketers)
- `list_accounts` — `GET /marketers` (https://amplifyv01.docs.apiary.io/#reference/marketers)
- `list_campaigns` — `GET /marketers/{account_id}/campaigns` (https://amplifyv01.docs.apiary.io/#reference/campaigns)
- `get_report` — `GET /reports/marketers/{account_id}/periodic` (https://amplifyv01.docs.apiary.io/#reference/performance-reporting)
- `pause_resume` — `PUT /campaigns/{campaign_id}` (https://amplifyv01.docs.apiary.io/#reference/campaigns)
- ~~`update_budget`~~ not offered: Budgets are separate entities referenced by campaigns (and possibly shared between them): the amount is changed with PUT /budgets/{budgetId} (https://amplifyv01.docs.apiary.io/#reference/budgets), and the Campaign update does not accept a budget amount ('Only the following Campaign properties are updatable: name, enabled, cpc, targeting…'). The vocabulary's campaign_id is not a budget id.

## Credentials

- `PLATFORM_MCP_OUTBRAIN_OB_TOKEN` — Amplify API token, sent as the OB-TOKEN-V1 header. Obtain it with `curl -u USER:PASSWORD https://api.outbrain.com/amplify/v0.1/login` (Basic auth; the response is {"OB-TOKEN-V1": "…"}); tokens last 30 days, so re-issue and replace it monthly. Amplify API access requires Outbrain's approval.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve outbrain   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve outbrain
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve outbrain   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/outbrain-mcp`. Python and TypeScript serve identical tools.
