# Lazada Sponsored Solutions MCP server

Category: **ads** · Docs: https://open.lazada.com/apps/doc/api?path=%2Fsponsor%2Fsolutions%2Fcampaign%2FsearchCampaignList · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/lazada_sponsored_solutions.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /sponsor/solutions/account/getAccountSignInfo` (https://open.lazada.com/apps/doc/api?path=%2Fsponsor%2Fsolutions%2Faccount%2FgetAccountSignInfo)
- `list_campaigns` — `GET /sponsor/solutions/campaign/searchCampaignList` (https://open.lazada.com/apps/doc/api?path=%2Fsponsor%2Fsolutions%2Fcampaign%2FsearchCampaignList)
- `get_report` — `GET /sponsor/solutions/report/getDiscoveryReportCampaign` (https://open.lazada.com/apps/doc/api?path=%2Fsponsor%2Fsolutions%2Freport%2FgetDiscoveryReportCampaign)
- `update_budget` — `POST /sponsor/solutions/campaign/updateCampaign` (https://open.lazada.com/apps/doc/api?path=%2Fsponsor%2Fsolutions%2Fcampaign%2FupdateCampaign)
- `pause_resume` — `POST /sponsor/solutions/campaign/updateCampaign` (https://open.lazada.com/apps/doc/api?path=%2Fsponsor%2Fsolutions%2Fcampaign%2FupdateCampaign)
- ~~`list_accounts`~~ not offered: The Sponsored Solutions API acts for the seller whose token is used; its account calls report agreement status and auto top-up settings (getAccountSignInfo, getLatestSignInfo, sign, wallet …AutoTopUp…), none lists ad accounts (Sponsored Solutions API category, https://open.lazada.com/apps/doc/api).

## Credentials

- `PLATFORM_MCP_LAZADA_SPONSORED_SOLUTIONS_APP_KEY` — App Key of your Lazada Open Platform app with the Sponsored Solutions API permission (App Console).
- `PLATFORM_MCP_LAZADA_SPONSORED_SOLUTIONS_APP_SECRET` — App Secret of the same app; signs every call and the token refresh (uppercase hex HMAC-SHA256 over the API name + sorted name/value pairs). Never sent on the wire.
- `PLATFORM_MCP_LAZADA_SPONSORED_SOLUTIONS_REFRESH_TOKEN` — Seller refresh_token from /auth/token/create after the seller authorised the app; the runtime mints access tokens with the signed /auth/token/refresh (https://auth.lazada.com/rest) and keeps the refresh_token it returns ('The refresh token cannot be refreshed': when refresh_expires_in runs out the seller must re-authorise). Set PLATFORM_MCP_STATE_DIR so the newest one survives restarts.
- `PLATFORM_MCP_LAZADA_SPONSORED_SOLUTIONS_API_DOMAIN` — Regional API host of the seller's venture: api.lazada.sg, api.lazada.com.my, api.lazada.com.ph, api.lazada.co.th, api.lazada.co.id or api.lazada.vn (Service Endpoints of each Sponsored Solutions API).

## Run

    uvx platform-mcp-hub serve lazada_sponsored_solutions          # Python
    npx -y platform-mcp-hub serve lazada_sponsored_solutions       # TypeScript
    claude mcp add lazada_sponsored_solutions -- uvx platform-mcp-hub serve lazada_sponsored_solutions

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/lazada_sponsored_solutions-mcp`. Python and TypeScript serve identical tools.
