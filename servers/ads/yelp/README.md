# Yelp Ads MCP server

Category: **ads** · Docs: https://docs.developer.yelp.com/docs/ads-api · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/yelp.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /programs/v1` (https://docs.developer.yelp.com/reference/get_program_list_all)
- `list_campaigns` — `GET /programs/v1` (https://docs.developer.yelp.com/reference/get_program_list_all)
- `pause_resume` — `POST /program/{campaign_id}/{op}/v1` (https://docs.developer.yelp.com/docs/ads-api#pause-program)
- ~~`list_accounts`~~ not offered: The credentials are bound to one payment account; the Ads API has no account listing (https://docs.developer.yelp.com/docs/ads-api lists only create, edit, end, status, pause and resume).
- ~~`get_report`~~ not offered: Reporting API v3 is asynchronous (POST https://api.yelp.com/v3/reporting/businesses/daily 'Requests a report … Use get_daily_reports_v3 to poll for report completion', https://docs.developer.yelp.com/reference/create_daily_reports_v3), keyed by business ids rather than programs, and authenticated with a Bearer API key on a different host from the Basic-auth partner API.
- ~~`update_budget`~~ not offered: Yelp CPC budgets are monthly, not daily: POST /v1/reseller/program/{program_id}/edit?budget= takes 'Monthly budget in cents' and answers with an async job_id (https://docs.developer.yelp.com/docs/ads-api#modify-program); a daily budget cannot be set.

## Credentials

- `PLATFORM_MCP_YELP_USERNAME` — Yelp Partner API username (the same Basic-auth credentials as the Data Ingestion API; issued by your Yelp account team, access is disabled by default: https://docs.developer.yelp.com/docs/ads-api).
- `PLATFORM_MCP_YELP_PASSWORD` — Yelp Partner API password (Basic HTTP authentication on partner-api.yelp.com).

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve yelp   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve yelp
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve yelp   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/yelp-mcp`. Python and TypeScript serve identical tools.
