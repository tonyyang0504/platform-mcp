# AdRoll MCP server

Category: **ads** · Docs: https://developers.nextroll.com/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/adroll.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /api/v1/organization/get` (https://apidocs.nextroll.com/crud-api/reference.html)
- `list_accounts` — `GET /api/v1/organization/get_advertisables` (https://apidocs.nextroll.com/crud-api/reference.html)
- `list_campaigns` — `GET /api/v1/advertisable/get_campaigns` (https://apidocs.nextroll.com/crud-api/reference.html)
- `get_report` — `GET /api/v1/report/campaign` (https://apidocs.nextroll.com/crud-api/reference.html)
- `pause_resume` — `PUT /api/v1/campaign/{op}` (https://apidocs.nextroll.com/crud-api/reference.html)
- ~~`update_budget`~~ not offered: "POST /api/v1/campaign/edit … budget: The new WEEKLY budget for the campaign" (with ui_budget_daily required); AdRoll stores weekly budgets and the adapter cannot convert a daily amount (https://apidocs.nextroll.com/crud-api/reference.html).

## Credentials

- `PLATFORM_MCP_ADROLL_TOKEN` — AdRoll Personal Access Token (dashboard > settings > Personal Access Tokens), sent as `Authorization: Token <PAT>` (https://apidocs.nextroll.com/guides/get-started.html).
- `PLATFORM_MCP_ADROLL_CLIENT_ID` — Client ID (consumer key) of your NextRoll developer application, sent in the `apikey` query parameter on every call.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve adroll   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve adroll
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve adroll   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/adroll-mcp`. Python and TypeScript serve identical tools.
