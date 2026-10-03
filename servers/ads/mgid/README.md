# MGID MCP server

Category: **ads** · Docs: https://help.mgid.com/api-advertisers · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/mgid.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /clients/{client_id}` (https://help.mgid.com/api-advertisers)
- `update_budget` — `PATCH /goodhits/clients/{client_id}/campaigns/{campaign_id}` (https://help.mgid.com/api-advertisers)
- `pause_resume` — `PATCH /goodhits/clients/{client_id}/campaigns/{campaign_id}` (https://help.mgid.com/api-advertisers)
- ~~`list_accounts`~~ not offered: The token works on one client id; there is no client list in the advertiser API (https://help.mgid.com/api-advertisers, 'Working with clients').
- ~~`list_campaigns`~~ not offered: GET /v1/goodhits/clients/{client_id}/campaigns answers an object keyed by campaign id ({"<campaign_id>": {id, name, status {id, name}, limitsFilter, …}}), not an array (https://help.mgid.com/api-advertisers, 'Getting a collection of client's advertising campaigns'); the runtime's result mapping lists arrays only.
- ~~`get_report`~~ not offered: GET /v1/goodhits/clients/{client_id}/campaigns-stat?dateInterval=interval&startDate&endDate answers an object keyed by campaign id ({"<campaign_id>": {campaign_id, imps, clicks, spent, avcpc}}), not an array (https://help.mgid.com/api-advertisers, 'Advertising campaigns daily statistics'); the runtime's result mapping lists arrays only.

## Credentials

- `PLATFORM_MCP_MGID_API_TOKEN` — 32-character MGID REST API token from the MGID Ads dashboard (Settings > API), sent as `Authorization: Bearer`.
- `PLATFORM_MCP_MGID_CLIENT_ID` — The advertiser's MGID client (account) id; every campaign path is /goodhits/clients/{client_id}/…

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve mgid   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve mgid
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve mgid   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/mgid-mcp`. Python and TypeScript serve identical tools.
