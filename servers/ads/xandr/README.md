# Microsoft Invest (Xandr DSP, discontinued) MCP server

Category: **ads** · Docs: https://learn.microsoft.com/en-us/xandr/digital-platform-api/api-getting-started · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/xandr.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /user?current` (https://learn.microsoft.com/en-us/xandr/digital-platform-api/user-service)
- `list_accounts` — `GET /advertiser` (https://learn.microsoft.com/en-us/xandr/digital-platform-api/advertiser-service)
- `list_campaigns` — `GET /line-item` (https://learn.microsoft.com/en-us/xandr/digital-platform-api/line-item-service)
- `pause_resume` — `PUT /line-item` (https://learn.microsoft.com/en-us/xandr/digital-platform-api/line-item-service)
- ~~`get_report`~~ not offered: Reporting is asynchronous: 'POST the report request to the Report Service', then poll 'GET https://api.appnexus.com/report?id=REPORT_ID' until execution_status is ready and download from report-download (https://learn.microsoft.com/en-us/xandr/digital-platform-api/report-service); one adapter call cannot request, poll and download.
- ~~`update_budget`~~ not offered: Seamless line items keep daily budgets per billing period: 'If you use budget_intervals, the following fields should not be used on the line-item object: … daily_budget' (https://learn.microsoft.com/en-us/xandr/digital-platform-api/line-item-service), so a budget change must target a specific budget_intervals element by id, which the vocabulary's campaign_id + daily_budget cannot address.

## Credentials

- `PLATFORM_MCP_XANDR_USERNAME` — Xandr / Microsoft Advertising platform API user name (an API-enabled user created through the API Onboarding Process).
- `PLATFORM_MCP_XANDR_PASSWORD` — Password of that API user. POST /auth {auth: {username, password}} returns a token valid for 2 hours after the last call (24-hour hard expiry); the runtime re-authenticates on expiry or 401 (the API allows 10 successful logins per 5 minutes).
- `PLATFORM_MCP_XANDR_ADVERTISER_ID` — Advertiser id that owns the line items; required for pause_resume (PUT /line-item?id=…&advertiser_id=…).

## Run

    uvx platform-mcp-hub serve xandr          # Python
    npx -y platform-mcp-hub serve xandr       # TypeScript
    claude mcp add xandr -- uvx platform-mcp-hub serve xandr

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/xandr-mcp`. Python and TypeScript serve identical tools.
