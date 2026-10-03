# Trustpilot MCP server

Category: **social** · Docs: https://developers.trustpilot.com/service-reviews-api/ · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/social/trustpilot.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /private/business-units/{business_unit_id}/reviews` (https://developers.trustpilot.com/business-units-api/)
- `read_mentions` — `GET /private/business-units/{business_unit_id}/reviews` (https://developers.trustpilot.com/business-units-api/)
- `reply_comment` — `POST /private/reviews/{comment_id}/reply` (https://developers.trustpilot.com/service-reviews-api/)
- ~~`publish_text`~~ not offered: Businesses cannot publish posts; the Service Reviews API only replies to, tags and reads reviews (https://developers.trustpilot.com/service-reviews-api/).
- ~~`publish_image`~~ not offered: No publishing endpoint exists (https://developers.trustpilot.com/service-reviews-api/).
- ~~`read_comments`~~ not offered: Reviews have no comment threads, only a single companyReply (https://developers.trustpilot.com/service-reviews-api/); reviews are exposed as read_mentions.
- ~~`delete`~~ not offered: A business cannot delete reviews; only its own reply can be deleted (DELETE /v1/private/reviews/{reviewId}/reply, https://developers.trustpilot.com/service-reviews-api/), which is not a post.
- ~~`analytics_post`~~ not offered: No per-review metrics endpoint beyond likes (https://developers.trustpilot.com/service-reviews-api/).

## Credentials

- `PLATFORM_MCP_TRUSTPILOT_CLIENT_ID` — Trustpilot API key (Client ID); HTTP Basic username on the refresh request ('Authorization: Basic [BASE64_ENCODED(API_KEY:API_SECRET)]', https://developers.trustpilot.com/authentication).
- `PLATFORM_MCP_TRUSTPILOT_CLIENT_SECRET` — Trustpilot API secret; HTTP Basic password on the refresh request.
- `PLATFORM_MCP_TRUSTPILOT_REFRESH_TOKEN` — Business-user refresh token from the authorization-code or password grant. 'Access tokens expire after 100 hours and refresh tokens expire after 30 days'; the runtime mints access tokens from it and keeps a returned new refresh token (PLATFORM_MCP_STATE_DIR persists it).
- `PLATFORM_MCP_TRUSTPILOT_BUSINESS_UNIT_ID` — Business unit id (GET /v1/business-units/find?name=<domain> with the API key).
- `PLATFORM_MCP_TRUSTPILOT_BUSINESS_USER_ID` — Id of the business user replies are authored by (authorBusinessUserId).

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve trustpilot   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve trustpilot
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve trustpilot   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/trustpilot-mcp`. Python and TypeScript serve identical tools.
