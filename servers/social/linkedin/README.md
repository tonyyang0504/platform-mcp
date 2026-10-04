# LinkedIn MCP server

Category: **social** · Docs: https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/posts-api · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/social/linkedin.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /v2/userinfo` (https://learn.microsoft.com/en-us/linkedin/consumer/integrations/self-serve/sign-in-with-linkedin-v2)
- `read_comments` — `GET /rest/socialActions/{post_id}/comments` (https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/comments-api)
- `reply_comment` — `POST /rest/socialActions/{comment_id}/comments` (https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/comments-api)
- `read_mentions` — `GET /rest/organizationalEntityNotifications?q=criteria&actions=List(SHARE_MENTION)` (https://learn.microsoft.com/en-us/linkedin/marketing/community-management/organizations/organization-social-action-notifications)
- `delete` — `DELETE /rest/posts/{post_id}` (https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/posts-api)
- `analytics_post` — `GET /rest/socialMetadata/{post_id}` (https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/social-metadata-api)
- ~~`publish_text`~~ not offered: POST /rest/posts answers 201 with the Post id only in a header: 'the response header x-restli-id contains the Post ID' (https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/posts-api); the runtime maps response bodies only, so the required `id` could not be returned.
- ~~`publish_image`~~ not offered: An image post first needs 'uploading an image asset to obtain an Image URN (urn:li:image:{id})' via the Images API (initializeUpload, then PUT the bytes) before POST /rest/posts (https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/images-api) — not a single call.

## Credentials

- `PLATFORM_MCP_LINKEDIN_CLIENT_ID` — Client id of a LinkedIn app with the Community Management API product (scopes w_organization_social, r_organization_social, plus openid profile for me).
- `PLATFORM_MCP_LINKEDIN_CLIENT_SECRET` — The app's client secret (form body of the refresh_token grant at https://www.linkedin.com/oauth/v2/accessToken).
- `PLATFORM_MCP_LINKEDIN_REFRESH_TOKEN` — Programmatic refresh token from the 3-legged flow (approved Marketing/Community Management partners; valid about one year). The runtime mints 60-day access tokens from it.
- `PLATFORM_MCP_LINKEDIN_AUTHOR_URN` — Organization URN the member administers and acts as, e.g. urn:li:organization:5515715 (comment actor and the organizationalEntity of read_mentions).

## Run

    uvx platform-mcp-hub serve social/linkedin          # Python
    npx -y platform-mcp-hub serve social/linkedin       # TypeScript
    claude mcp add linkedin -- uvx platform-mcp-hub serve social/linkedin

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/linkedin-social-mcp`. Python and TypeScript serve identical tools.
