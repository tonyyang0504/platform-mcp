# Google Ads MCP server

Category: **ads** · Docs: https://developers.google.com/google-ads/api/docs/start · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/google.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /customers:listAccessibleCustomers` (https://developers.google.com/google-ads/api/rest/examples)
- `list_accounts` — `POST /customers/{customer_id}/googleAds:search` (https://developers.google.com/google-ads/api/docs/account-management/get-account-hierarchy)
- `list_campaigns` — `POST /customers/{account_id}/googleAds:search` (https://developers.google.com/google-ads/api/rest/common/search)
- `get_report` — `POST /customers/{account_id}/googleAds:search` (https://developers.google.com/google-ads/api/docs/query/date-ranges)
- `pause_resume` — `POST /customers/{customer_id}/campaigns:mutate` (https://developers.google.com/google-ads/api/rest/examples)
- ~~`update_budget`~~ not offered: campaignBudgets:mutate updates the CampaignBudget resource (customers/{cid}/campaignBudgets/{budget_id}), whose id is not the campaign id and needs a prior GAQL lookup, with amountMicros (amount x 1,000,000); two calls, a composed resource name and a scaled amount.

## Credentials

- `PLATFORM_MCP_GOOGLE_CLIENT_ID` — OAuth 2.0 client id (Google Cloud console > Credentials) of the app that the Google Ads user authorised with scope https://www.googleapis.com/auth/adwords.
- `PLATFORM_MCP_GOOGLE_CLIENT_SECRET` — The OAuth client's secret; sent in the form body of the refresh_token grant.
- `PLATFORM_MCP_GOOGLE_REFRESH_TOKEN` — Refresh token obtained once through Google's consent flow (offline access, scope https://www.googleapis.com/auth/adwords); the runtime mints hourly access tokens from it.
- `PLATFORM_MCP_GOOGLE_DEVELOPER_TOKEN` — Google Ads API developer token (manager account > Admin > API Center), sent as the `developer-token` header on every call; Test-access tokens only work against test accounts.
- `PLATFORM_MCP_GOOGLE_CUSTOMER_ID` — Google Ads customer id (10 digits, no dashes) of the account being managed: pause_resume mutates campaigns under it, and list_accounts reads its customer_client hierarchy (itself plus direct clients when it is a manager). When the user reaches it through a manager account, also set login_customer_id.
- `PLATFORM_MCP_GOOGLE_LOGIN_CUSTOMER_ID` — Manager customer id (digits, no dashes) sent as `login-customer-id` when the user reaches client accounts through a manager account; leave unset for direct access.
- `PLATFORM_MCP_GOOGLE_ENV` — Vendor environment (default production): sandbox = production host with test accounts or test keys. Credentials are the environment's own; see adapter.environments in the catalog entry.
- `PLATFORM_MCP_GOOGLE_BASE_URL` — Optional https base URL override (a mock or a private gateway); replaces the selected environment's base_url. Never echoed in errors.

## Run

    uvx platform-mcp-hub serve google          # Python
    npx -y platform-mcp-hub serve google       # TypeScript
    claude mcp add google -- uvx platform-mcp-hub serve google

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/google-mcp`. Python and TypeScript serve identical tools.
