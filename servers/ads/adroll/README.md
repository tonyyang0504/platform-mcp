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

    uvx platform-mcp-hub serve adroll          # Python
    npx -y platform-mcp-hub serve adroll       # TypeScript
    claude mcp add adroll -- uvx platform-mcp-hub serve adroll

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/adroll-mcp`. Python and TypeScript serve identical tools.
