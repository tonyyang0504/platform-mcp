# Meta Ads MCP server

Category: **ads** · Docs: https://developers.facebook.com/docs/marketing-apis · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/meta.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /me` (https://developers.facebook.com/docs/graph-api/reference/user/)
- `list_accounts` — `GET /me/adaccounts` (https://developers.facebook.com/docs/marketing-api/reference/ad-account/)
- `list_campaigns` — `GET /{account_id}/campaigns` (https://developers.facebook.com/docs/marketing-api/reference/ad-account/campaigns/)
- `update_budget` — `POST /{campaign_id}` (https://developers.facebook.com/docs/marketing-api/reference/ad-campaign-group/)
- `pause_resume` — `POST /{campaign_id}` (https://developers.facebook.com/docs/marketing-api/reference/ad-campaign-group/)
- ~~`get_report`~~ not offered: GET /{object_id}/insights takes a custom range only as the single object parameter `time_range={'since':YYYY-MM-DD,'until':YYYY-MM-DD}` (https://developers.facebook.com/docs/marketing-api/reference/ad-account/insights/: since/until are properties of that object, not parameters); the runtime cannot build it from date_from/date_to. A fixed `date_preset` (e.g. last_7d) is documented but would silently ignore the required date_from/date_to, so it is not mapped.

## Credentials

- `PLATFORM_MCP_META_ACCESS_TOKEN` — Long-lived user or Business Manager system-user access token with ads_read (reads) and ads_management (budget updates), from an app with the Marketing API product; sent as `Authorization: Bearer`.

## Run

    uvx platform-mcp-hub serve meta          # Python
    npx -y platform-mcp-hub serve meta       # TypeScript
    claude mcp add meta -- uvx platform-mcp-hub serve meta

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/meta-mcp`. Python and TypeScript serve identical tools.
