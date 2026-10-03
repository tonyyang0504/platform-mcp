# X MCP server

Category: **social** · Docs: https://docs.x.com/x-api/posts/create-post · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/social/x.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /2/users/me` (https://docs.x.com/x-api/users/get-my-user)
- `publish_text` — `POST /2/tweets` (https://docs.x.com/x-api/posts/create-post)
- `read_comments` — `GET /2/tweets/search/recent` (https://docs.x.com/x-api/posts/search-recent-posts)
- `reply_comment` — `POST /2/tweets` (https://docs.x.com/x-api/posts/create-post)
- `read_mentions` — `GET /2/users/{user_id}/mentions` (https://docs.x.com/x-api/users/get-mentions)
- `delete` — `DELETE /2/tweets/{post_id}` (https://docs.x.com/x-api/posts/delete-post)
- `analytics_post` — `GET /2/tweets/{post_id}` (https://docs.x.com/x-api/posts/get-post-by-id)
- ~~`publish_image`~~ not offered: Media must be uploaded first: 'Upload media first with the chunked upload endpoints, then pass the returned media_id in media.media_ids' (https://docs.x.com/x-api/posts/create-post); the runtime has no file upload and makes one call per tool.

## Credentials

- `PLATFORM_MCP_X_CLIENT_ID` — OAuth 2.0 Client ID of the X app (Developer Console > Keys and tokens). Sent as the HTTP Basic username on POST https://api.x.com/2/oauth2/token (grant_type=refresh_token).
- `PLATFORM_MCP_X_CLIENT_SECRET` — OAuth 2.0 Client Secret of a CONFIDENTIAL client ('Web App and Automated App or bots are confidential clients'; 'You don't need client id for confidential clients with a valid Authorization Header'); HTTP Basic password on the token request. Public clients (Native App, Single page App) are not supported by this entry.
- `PLATFORM_MCP_X_REFRESH_TOKEN` — Refresh token from a one-time OAuth 2.0 Authorization Code Flow with PKCE consent with scopes tweet.read tweet.write users.read offline.access ('If the scope offline.access is applied an OAuth 2.0 refresh token will be issued', https://docs.x.com/resources/fundamentals/authentication/oauth-2-0/authorization-code). Access tokens (2 h) are minted from it; a new refresh token returned by the grant replaces the old one in memory (and in PLATFORM_MCP_STATE_DIR/x.json when that is set).
- `PLATFORM_MCP_X_USER_ID` — Numeric X user id of the authorizing account (data.id from the `me` tool, GET /2/users/me); read_mentions calls /2/users/<user_id>/mentions. Env: PLATFORM_MCP_X_USER_ID.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve x   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve x
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve x   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/x-mcp`. Python and TypeScript serve identical tools.
