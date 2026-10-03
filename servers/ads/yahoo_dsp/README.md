# Yahoo DSP MCP server

Category: **ads** · Docs: https://help.yahooinc.com/dsp-api/docs/dsp-api-help-home · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/yahoo_dsp.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /traffic/seats` (https://help.yahooinc.com/dsp-api/docs/seats)
- `list_accounts` — `GET /traffic/advertisers` (https://help.yahooinc.com/dsp-api/docs/advertisers)
- `list_campaigns` — `GET /traffic/campaigns` (https://help.yahooinc.com/dsp-api/docs/campaigns)
- `pause_resume` — `PUT /traffic/campaigns/{campaign_id}` (https://help.yahooinc.com/dsp-api/docs/campaigns)
- ~~`get_report`~~ not offered: The Reporting API is asynchronous: 'To create a new report, call the endpoint using the POST method… To retrieve report status and a URL, call the endpoint using the GET method and specify the customerReportId', and the finished report is a CSV behind a temporary URL (https://help.yahooinc.com/dsp-api/docs/resources) — no single call returns rows.
- ~~`update_budget`~~ not offered: Campaign budgets live in budgetSchedules, and an update must name the schedule: budget schedule 'id' is 'Required' on Update, as are 'startDate', 'endDate' and 'scheduleBudgetType' (https://help.yahooinc.com/dsp-api/docs/campaigns); the vocabulary's update_budget carries only campaign_id and daily_budget.

## Credentials

- `PLATFORM_MCP_YAHOO_DSP_CLIENT_ID` — DSP API client ID (DSP UI → your name → My Account → Activate; shown once). The JWT issuer is built as idb2b.dsp.dspapi.<client_id>, so enter the ID without that prefix.
- `PLATFORM_MCP_YAHOO_DSP_CLIENT_SECRET` — DSP API client secret shown with the client ID; it signs the HS256 client assertion.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve yahoo_dsp   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve yahoo_dsp
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve yahoo_dsp   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/yahoo_dsp-mcp`. Python and TypeScript serve identical tools.
