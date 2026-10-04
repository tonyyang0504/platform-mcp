# Apple Ads (formerly Apple Search Ads) MCP server

Category: **ads** · Docs: https://developer.apple.com/documentation/apple-ads-platform-api · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/apple_search_ads.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /v1/me` (https://developer.apple.com/documentation/apple-ads-platform-api/get-current-user-details)
- `list_accounts` — `GET /v1/acls` (https://developer.apple.com/documentation/apple-ads-platform-api/get-user-acls)
- `list_campaigns` — `POST /v1/campaigns/query` (https://developer.apple.com/documentation/apple-ads-platform-api/post-campaigns-query)
- `get_report` — `POST /v1/reports/apps/campaigns/query` (https://developer.apple.com/documentation/apple-ads-platform-api/get-app-campaign-reports)
- `update_budget` — `PUT /v1/campaigns/{campaign_id}` (https://developer.apple.com/documentation/apple-ads-platform-api/put-campaigns-_id_)
- `pause_resume` — `PUT /v1/campaigns/{campaign_id}` (https://developer.apple.com/documentation/apple-ads-platform-api/put-campaigns-_id_)

## Credentials

- `PLATFORM_MCP_APPLE_SEARCH_ADS_CLIENT_ID` — Apple Ads API clientId (SEARCHADS.…) shown after uploading your public key under Account Settings > API (https://developer.apple.com/documentation/apple-ads-platform-api/implementing-oauth-for-the-apple-ads-platform-api).
- `PLATFORM_MCP_APPLE_SEARCH_ADS_CLIENT_SECRET` — The client secret JWT you sign yourself with your ES256 private key (header kid=keyId; claims sub=clientId, iss=teamId, aud=https://appleid.apple.com, exp at most 180 days after iat). The runtime does not sign it: regenerate and replace it before it expires.
- `PLATFORM_MCP_APPLE_SEARCH_ADS_AP_CONTEXT` — The full X-AP-Context header value for ad-account-scoped calls, exactly `adAccountId=<ad account id>` (ids from GET /v1/acls, i.e. list_accounts).

## Run

    uvx platform-mcp-hub serve apple_search_ads          # Python
    npx -y platform-mcp-hub serve apple_search_ads       # TypeScript
    claude mcp add apple_search_ads -- uvx platform-mcp-hub serve apple_search_ads

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/apple_search_ads-mcp`. Python and TypeScript serve identical tools.
