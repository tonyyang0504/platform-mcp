# Awin MCP server

Category: **ads** · Docs: https://help.awin.com/developers/apidocs · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/awin.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /accounts` (https://help.awin.com/apidocs/returns-information-about-accounts-for-a-given-user)
- `list_accounts` — `GET /accounts` (https://help.awin.com/apidocs/returns-information-about-accounts-for-a-given-user)
- `get_report` — `GET /advertisers/{account_id}/reports/publisher` (https://help.awin.com/apidocs/get-publisher-performance-report)
- ~~`list_campaigns`~~ not offered: Awin programmes have no campaign objects; the only 'campaign' is a free-text click parameter (&campaign=) aggregated by GET /advertisers/{advertiserId}/reports/campaign (https://help.awin.com/apidocs/get-campaign-data-for-advertiser-report), which is a report, not a list of campaigns with ids.
- ~~`update_budget`~~ not offered: No budget endpoint: the advertiser API covers transactions, performance reports, publishers, commission groups, offers, product feeds and conversions (https://help.awin.com/apidocs/for-advertisers); Awin is pay-per-commission.
- ~~`pause_resume`~~ not offered: No programme or campaign status endpoint in the advertiser API (https://help.awin.com/apidocs/for-advertisers).

## Credentials

- `PLATFORM_MCP_AWIN_API_TOKEN` — Personal Awin API token (https://ui.awin.com/awin-api > 'Show my API token'), sent as `Authorization: Bearer`. It is user-level: it reaches every advertiser account the user has at least viewer access to. Advertiser API access requires an Accelerate or Advanced plan.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve awin   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve awin
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve awin   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/awin-mcp`. Python and TypeScript serve identical tools.
