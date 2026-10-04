# Amazon DSP MCP server

Category: **ads** · Docs: https://advertising.amazon.com/API/docs/en-us/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/amazon_dsp.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /v2/profiles/{profile_id}` (https://advertising.amazon.com/API/docs/en-us/reference/profiles)
- `list_accounts` — `GET /dsp/advertisers` (https://advertising.amazon.com/API/docs/en-us/dsp-advertiser/#tag/Advertiser/paths/~1dsp~1advertisers/get)
- ~~`get_report`~~ not offered: DSP reports are asynchronous: "POST /accounts/{dspAccountId}/dsp/reports" then "GET …/dsp/reports/{reportId}" until the file is ready (Amazon Ads API Postman collection, https://github.com/amzn/ads-advanced-tools-docs, Reporting > DSP report); the runtime has no report polling.
- ~~`list_campaigns`~~ not offered: DSP orders / line items are not in Amazon's public API collection and their reference page (https://advertising.amazon.com/API/docs/en-us/dsp-orders/) answers "The requested document was not found"; not mapped rather than guessed.
- ~~`update_budget`~~ not offered: No publicly documented DSP order/line-item update endpoint could be opened (see list_campaigns).
- ~~`pause_resume`~~ not offered: No publicly documented DSP order/line-item update endpoint could be opened (see list_campaigns).

## Credentials

- `PLATFORM_MCP_AMAZON_DSP_CLIENT_ID` — Login with Amazon client id of the app approved for the Amazon Ads API; also sent as the Amazon-Advertising-API-ClientId header.
- `PLATFORM_MCP_AMAZON_DSP_CLIENT_SECRET` — The LWA client secret (form body of the refresh_token grant).
- `PLATFORM_MCP_AMAZON_DSP_REFRESH_TOKEN` — LWA refresh token from the advertiser's consent (scope advertising::campaign_management); the runtime mints hourly access tokens from it at https://api.amazon.com/auth/o2/token.
- `PLATFORM_MCP_AMAZON_DSP_API_HOST` — Regional Amazon Ads API host: advertising-api.amazon.com (North America), advertising-api-eu.amazon.com (Europe) or advertising-api-fe.amazon.com (Far East).
- `PLATFORM_MCP_AMAZON_DSP_PROFILE_ID` — Advertising profile id of the DSP entity (from GET /v2/profiles; accountInfo.type must be `agency`), sent as the Amazon-Advertising-API-Scope header.

## Run

    uvx platform-mcp-hub serve amazon_dsp          # Python
    npx -y platform-mcp-hub serve amazon_dsp       # TypeScript
    claude mcp add amazon_dsp -- uvx platform-mcp-hub serve amazon_dsp

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/amazon_dsp-mcp`. Python and TypeScript serve identical tools.
