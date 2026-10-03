# Threads MCP server

Category: **social** · Docs: https://developers.facebook.com/docs/threads/posts · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/social/threads.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /me` (https://developers.facebook.com/docs/threads/threads-profiles)
- `publish_text` — `POST /me/threads` (https://developers.facebook.com/docs/threads/reference/publishing)
- `read_comments` — `GET /{post_id}/replies` (https://developers.facebook.com/docs/threads/retrieve-and-manage-replies/replies-and-conversations)
- `reply_comment` — `POST /me/threads` (https://developers.facebook.com/docs/threads/reference/publishing)
- `read_mentions` — `GET /me/mentions` (https://developers.facebook.com/docs/threads/threads-mentions)
- `delete` — `DELETE /{post_id}` (https://developers.facebook.com/docs/threads/posts/delete-posts)
- `analytics_post` — `GET /{post_id}/insights` (https://developers.facebook.com/docs/threads/insights)
- ~~`publish_image`~~ not offered: Image posts take two calls: 'Create a media container ... using the POST /{threads-user-id}/threads endpoint' then 'Publish the media container using the POST /{threads-user-id}/threads_publish endpoint' (https://developers.facebook.com/docs/threads/posts); auto_publish_text 'only works for text posts' (https://developers.facebook.com/docs/threads/reference/publishing).

## Credentials

- `PLATFORM_MCP_THREADS_ACCESS_TOKEN` — Threads user access token (long-lived, 60 days; refresh with GET /refresh_access_token) of the Threads profile, from an app with the Threads use case; scopes threads_basic, threads_content_publish, threads_read_replies, threads_manage_replies, threads_manage_mentions, threads_manage_insights, threads_delete. Sent as the access_token query parameter, as every Threads example does (https://developers.facebook.com/docs/threads/posts).

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve threads   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve threads
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve threads   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/threads-mcp`. Python and TypeScript serve identical tools.
