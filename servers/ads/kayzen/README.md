# Kayzen MCP server

Category: **ads** · Docs: https://developers.kayzen.io/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/kayzen.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /v1/balance` (https://developers.kayzen.io/reference/view-balance)
- `list_campaigns` — `GET /v1/campaigns` (https://developers.kayzen.io/reference/campaigns)
- `get_report` — `POST /v1/report_data` (https://developers.kayzen.io/reference/report-data)
- `update_budget` — `PATCH /v1/campaigns/{campaign_id}` (https://developers.kayzen.io/reference/update-campaign)
- `pause_resume` — `PUT /v1/campaigns/{campaign_id}/status` (https://developers.kayzen.io/reference/pauseresume-campaign)
- ~~`list_accounts`~~ not offered: The API reference (https://developers.kayzen.io/reference) has no advertiser-listing endpoint; calls act on the API key's advertiser, and enterprise admins pass another 'Advertiser ID (for enterprise admin user)' explicitly (List Campaigns: 'The advertiser of the api key becomes the default advertiser. To switch advertisers, pass the advertiser id of that advertiser').

## Credentials

- `PLATFORM_MCP_KAYZEN_API_BASIC` — base64(<API_Key>:<API_Secret_Key>) — the Kayzen API key and secret (Kayzen UI > Account > API Key; 'Obtaining your Kayzen API key') joined by a colon and Base64-encoded, e.g. `printf '%s' 'KEY:SECRET' | base64`. Sent as `Authorization: Basic …` on POST /v1/authentication/token only.
- `PLATFORM_MCP_KAYZEN_USERNAME` — Kayzen login email of the user the API key belongs to (token request body `username`).
- `PLATFORM_MCP_KAYZEN_PASSWORD` — Kayzen account password for that login (token request body `password`); the runtime exchanges it for a 30-minute bearer token and re-logs in on expiry or 401.
- `PLATFORM_MCP_KAYZEN_ADVERTISER_ID` — Kayzen advertiser id used by `me` (GET /v1/balance?advertiser_id=…). Leave empty to use the API key's default advertiser.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve kayzen   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve kayzen
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve kayzen   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/kayzen-mcp`. Python and TypeScript serve identical tools.
