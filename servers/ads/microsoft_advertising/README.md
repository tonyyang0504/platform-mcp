# Microsoft Advertising (Bing Ads) MCP server

Category: **ads** · Docs: https://learn.microsoft.com/en-us/advertising/guides/ · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/microsoft_advertising.json`; edit the catalog, not this file.

## Tools

- `me` — `POST https://clientcenter.api.bingads.microsoft.com/CustomerManagement/v13/Accounts/Search` (https://learn.microsoft.com/en-us/advertising/customer-management-service/searchaccounts?view=bingads-13)
- `list_accounts` — `POST https://clientcenter.api.bingads.microsoft.com/CustomerManagement/v13/Accounts/Search` (https://learn.microsoft.com/en-us/advertising/customer-management-service/searchaccounts?view=bingads-13)
- `list_campaigns` — `POST /CampaignManagement/v13/Campaigns/QueryByAccountId` (https://learn.microsoft.com/en-us/advertising/campaign-management-service/getcampaignsbyaccountid?view=bingads-13)
- `update_budget` — `PUT /CampaignManagement/v13/Campaigns` (https://learn.microsoft.com/en-us/advertising/campaign-management-service/updatecampaigns?view=bingads-13)
- `pause_resume` — `PUT /CampaignManagement/v13/Campaigns` (https://learn.microsoft.com/en-us/advertising/campaign-management-service/updatecampaigns?view=bingads-13)
- ~~`get_report`~~ not offered: Reporting is asynchronous: SubmitGenerateReport returns a ReportRequestId, PollGenerateReport is polled until Success and the report is a zipped CSV/TSV/XML file at ReportDownloadUrl; the runtime makes one call per tool.

## Credentials

- `PLATFORM_MCP_MICROSOFT_ADVERTISING_CLIENT_ID` — Application (client) id of the Microsoft Entra app registration used for the Microsoft Advertising consent.
- `PLATFORM_MCP_MICROSOFT_ADVERTISING_CLIENT_SECRET` — The app's client secret; required for web apps, omit for native/public clients.
- `PLATFORM_MCP_MICROSOFT_ADVERTISING_REFRESH_TOKEN` — Refresh token from the authorization-code flow with scope https://ads.microsoft.com/msads.manage offline_access; the runtime mints access tokens from it at https://login.microsoftonline.com/common/oauth2/v2.0/token.
- `PLATFORM_MCP_MICROSOFT_ADVERTISING_DEVELOPER_TOKEN` — Microsoft Advertising developer token (Developer Portal > Account), sent as the DeveloperToken header.
- `PLATFORM_MCP_MICROSOFT_ADVERTISING_CUSTOMER_ID` — Manager account (customer) id sent as the CustomerId header; list_accounts searches this customer's accounts.
- `PLATFORM_MCP_MICROSOFT_ADVERTISING_ACCOUNT_ID` — Ad account id sent as the CustomerAccountId header; it must equal the AccountId in campaign calls, so pass the same id as list_campaigns' account_id.
- `PLATFORM_MCP_MICROSOFT_ADVERTISING_ENV` — Vendor environment (default production): sandbox = https://campaign.api.sandbox.bingads.microsoft.com. Credentials are the environment's own; see adapter.environments in the catalog entry.
- `PLATFORM_MCP_MICROSOFT_ADVERTISING_BASE_URL` — Optional https base URL override (a mock or a private gateway); replaces the selected environment's base_url. Never echoed in errors.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve microsoft_advertising   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve microsoft_advertising
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve microsoft_advertising   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/microsoft_advertising-mcp`. Python and TypeScript serve identical tools.
