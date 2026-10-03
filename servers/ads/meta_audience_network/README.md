# Meta Audience Network MCP server

Category: **ads** · Docs: https://developers.facebook.com/docs/audience-network/optimization/report-api/guide-v2 · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/meta_audience_network.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /me` (https://developers.facebook.com/docs/graph-api/reference/user/)
- `get_report` — `GET /{account_id}/adnetworkanalytics` (https://developers.facebook.com/docs/audience-network/optimization/report-api/guide-v2)
- ~~`list_accounts`~~ not offered: The Audience Network Reporting API is queried per Business, property or app id ("GET /<ID>/adnetworkanalytics", https://developers.facebook.com/docs/audience-network/optimization/report-api/guide-v2); it has no account listing, so pass that id as account_id.
- ~~`list_campaigns`~~ not offered: Audience Network is a publisher monetisation product; its Reporting API reports requests, impressions, clicks and revenue and has no advertiser campaigns (https://developers.facebook.com/docs/audience-network/optimization/report-api/guide-v2).
- ~~`update_budget`~~ not offered: No campaigns or budgets exist on the publisher side of Audience Network (https://developers.facebook.com/docs/audience-network/optimization/report-api/guide-v2).
- ~~`pause_resume`~~ not offered: No campaigns exist on the publisher side of Audience Network (https://developers.facebook.com/docs/audience-network/optimization/report-api/guide-v2).

## Credentials

- `PLATFORM_MCP_META_AUDIENCE_NETWORK_ACCESS_TOKEN` — Long-lived Meta User Access Token with the read_audience_network_insights permission (system user tokens are not supported by this endpoint); long-lived user tokens last about 60 days and must then be renewed.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve meta_audience_network   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve meta_audience_network
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve meta_audience_network   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/meta_audience_network-mcp`. Python and TypeScript serve identical tools.
