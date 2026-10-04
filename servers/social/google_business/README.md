# Google Business Profile MCP server

Category: **social** · Docs: https://developers.google.com/my-business/content/posts-data · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/social/google_business.json`; edit the catalog, not this file.

## Tools

- `me` — `GET https://mybusinessaccountmanagement.googleapis.com/v1/accounts` (https://developers.google.com/my-business/reference/accountmanagement/rest/v1/accounts/list)
- `publish_text` — `POST /accounts/{account_id}/locations/{location_id}/localPosts` (https://developers.google.com/my-business/reference/rest/v4/accounts.locations.localPosts/create)
- `publish_image` — `POST /accounts/{account_id}/locations/{location_id}/localPosts` (https://developers.google.com/my-business/reference/rest/v4/accounts.locations.localPosts/create)
- `read_mentions` — `GET /accounts/{account_id}/locations/{location_id}/reviews` (https://developers.google.com/my-business/reference/rest/v4/accounts.locations.reviews/list)
- `reply_comment` — `PUT /accounts/{account_id}/locations/{location_id}/reviews/{comment_id}/reply` (https://developers.google.com/my-business/reference/rest/v4/accounts.locations.reviews/updateReply)
- `delete` — `DELETE /accounts/{account_id}/locations/{location_id}/localPosts/{post_id}` (https://developers.google.com/my-business/reference/rest/v4/accounts.locations.localPosts/delete)
- ~~`read_comments`~~ not offered: Local posts carry no comments in the LocalPost resource (https://developers.google.com/my-business/reference/rest/v4/accounts.locations.localPosts); customer feedback is reviews, exposed as read_mentions.
- ~~`analytics_post`~~ not offered: localPosts.reportInsights is a location-wide POST taking localPostNames plus a basicRequest with metricRequests and a timeRange (https://developers.google.com/my-business/reference/rest/v4/accounts.locations.localPosts/reportInsights); the vocabulary carries no time range.

## Credentials

- `PLATFORM_MCP_GOOGLE_BUSINESS_CLIENT_ID` — OAuth 2.0 client id (Google Cloud console, Clients page) of the app the user consented to.
- `PLATFORM_MCP_GOOGLE_BUSINESS_CLIENT_SECRET` — The OAuth client's secret; sent with client_id, refresh_token and grant_type=refresh_token in the form body of POST https://oauth2.googleapis.com/token (https://developers.google.com/identity/protocols/oauth2/web-server#offline).
- `PLATFORM_MCP_GOOGLE_BUSINESS_REFRESH_TOKEN` — Refresh token from a one-time authorization-code consent with access_type=offline and the scopes https://www.googleapis.com/auth/business.manage. 'Refresh tokens are valid until the user revokes access or the refresh token expires'; the runtime mints 1-hour access tokens from it.
- `PLATFORM_MCP_GOOGLE_BUSINESS_ACCOUNT_ID` — Business Profile account id (digits after accounts/ in GET https://mybusinessaccountmanagement.googleapis.com/v1/accounts).
- `PLATFORM_MCP_GOOGLE_BUSINESS_LOCATION_ID` — Location id (digits after locations/) of the verified location that posts and reviews belong to.
- `PLATFORM_MCP_GOOGLE_BUSINESS_LANGUAGE_CODE` — languageCode of new local posts, e.g. en-US (optional).

## Run

    uvx platform-mcp-hub serve google_business          # Python
    npx -y platform-mcp-hub serve google_business       # TypeScript
    claude mcp add google_business -- uvx platform-mcp-hub serve google_business

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/google_business-mcp`. Python and TypeScript serve identical tools.
