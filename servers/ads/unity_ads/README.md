# Unity Ads MCP server

Category: **ads** · Docs: https://docs.unity.com/en-us/grow/acquire/management/acquire-rest-apis · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/unity_ads.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /apps` (https://services.docs.unity.com/advertise/v1/#tag/Apps/operation/advertise-listApps)
- `list_accounts` — `GET /apps` (https://services.docs.unity.com/advertise/v1/#tag/Apps/operation/advertise-listApps)
- `list_campaigns` — `GET /apps/{account_id}/campaigns` (https://services.docs.unity.com/advertise/v1/#tag/Campaigns/operation/advertise-listCampaigns)
- `update_budget` — `PATCH /apps/{campaign_set_id}/campaigns/{campaign_id}/budget` (https://services.docs.unity.com/advertise/v1/#tag/Campaigns/operation/advertise-updateCampaignBudget)
- `pause_resume` — `PATCH /apps/{campaign_set_id}/campaigns/{campaign_id}` (https://services.docs.unity.com/advertise/v1/#tag/Campaigns/operation/advertise-updateCampaign)
- ~~`get_report`~~ not offered: Acquisition statistics come from the separate Advertising Statistics API, which returns CSV ('retrieve acquisition statistics data in a CSV format', https://docs.unity.com/en-us/grow/acquire/management/acquire-rest-apis); the runtime reads JSON only.

## Credentials

- `PLATFORM_MCP_UNITY_ADS_KEY_ID` — Key ID of a Unity service account (Unity Cloud dashboard > Administration > Service accounts) with an Advertise API role (Viewer for reads, Campaigns Editor or Admin for budget changes); the HTTP Basic username.
- `PLATFORM_MCP_UNITY_ADS_SECRET_KEY` — The service account's secret key, the HTTP Basic password.
- `PLATFORM_MCP_UNITY_ADS_ORGANIZATION_ID` — Unity organization id (core id) that owns the Unity Ads advertiser apps; part of every path.
- `PLATFORM_MCP_UNITY_ADS_CAMPAIGN_SET_ID` — App (campaign set) id used by update_budget, since budget calls are addressed as /apps/{campaignSetId}/campaigns/{campaignId}/budget. Take it from list_accounts.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve unity_ads   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve unity_ads
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve unity_ads   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/unity_ads-mcp`. Python and TypeScript serve identical tools.
