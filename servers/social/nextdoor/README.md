# Nextdoor MCP server

Category: **social** · Docs: https://developer.nextdoor.com/reference/create-post.md · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/social/nextdoor.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /me/` (https://developer.nextdoor.com/reference/me-1)
- `publish_text` — `POST /post/create/` (https://developer.nextdoor.com/reference/create-post)
- `publish_image` — `POST /post/create/` (https://developer.nextdoor.com/reference/create-post)
- `delete` — `DELETE /post/` (https://developer.nextdoor.com/reference/delete-a-post)
- ~~`read_comments`~~ not offered: No per-post comments endpoint exists: comments come embedded in 'Get your posts' (GET /post/, the most recent posts of the account, https://developer.nextdoor.com/reference/get-your-posts), which cannot be addressed by post id.
- ~~`reply_comment`~~ not offered: POST /comment/ requires the post's share id (`id`) in addition to parent_comment_id (https://developer.nextdoor.com/reference/create-comment-to-a-post-create-reply-to-a-comment); a comment id alone cannot address the reply.
- ~~`read_mentions`~~ not offered: The Publish API has no mentions or notifications endpoint (https://developer.nextdoor.com/reference/get-your-posts lists only your own posts).
- ~~`analytics_post`~~ not offered: view_count and smartlink_click_count are only fields of the recent-posts list GET /post/ (https://developer.nextdoor.com/reference/get-your-posts), not retrievable by post id; business and entity pages are 'not supported at the moment' there.

## Credentials

- `PLATFORM_MCP_NEXTDOOR_ACCESS_TOKEN` — Publish API user access token: apply for access (Nextdoor Partnerships issue client_id / client_secret), send the user through https://www.nextdoor.com/v3/authorize/ with scopes openid post:write post:read comment:write profile:read, then exchange the code at POST https://auth.nextdoor.com/v2/token (https://developer.nextdoor.com/reference/sharing-get-access-token; expires_in 31536000 s in the documented example). Refresh it before expiry (https://developer.nextdoor.com/reference/sharing-refresh-access-token). Sent as 'Authorization: Bearer <access_token>'.
- `PLATFORM_MCP_NEXTDOOR_SECURE_PROFILE_ID` — Optional profile id from GET /me/profiles (https://developer.nextdoor.com/reference/me-copy) to post / delete as a business or other profile of the account instead of the default neighbor profile.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve social/nextdoor   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve social/nextdoor
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve social/nextdoor   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/nextdoor-social-mcp`. Python and TypeScript serve identical tools.
