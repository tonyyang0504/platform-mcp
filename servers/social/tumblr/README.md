# Tumblr MCP server

Category: **social** · Docs: https://www.tumblr.com/docs/en/api/v2 · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/social/tumblr.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /blog/{blog_identifier}/info` (https://www.tumblr.com/docs/en/api/v2#info---retrieve-blog-info)
- `analytics_post` — `GET /blog/{blog_identifier}/posts` (https://www.tumblr.com/docs/en/api/v2#posts--retrieve-published-posts)
- ~~`publish_text`~~ not offered: POST /v2/blog/{blog-identifier}/posts (Neue Post Format) is at the 'OAuth' authentication level: 'OAuth: Requires a signed request that meets the OAuth 1.0a Protocol', or an OAuth2 bearer token from the Authorization Code grant whose response carries 'expires_in: 2520' seconds and a refresh_token (Refresh Token grant). The runtime has no OAuth 1.0a request signer, no authorization-code flow and no refresh-token flow, and the Client Credentials grant it does support carries no user, so it cannot post to a blog (needs_runtime: OAuth 1.0a signing or OAuth2 refresh-token grant; https://www.tumblr.com/docs/en/api/v2#oauth2-authorization, https://www.tumblr.com/docs/en/api/v2#posts---createreblog-a-post-neue-post-format).
- ~~`publish_image`~~ not offered: Same OAuth-level create endpoint as publish_text (image blocks in NPF `content` need a media upload or a URL block, and the runtime has neither the user token nor an expression to spread `image_urls` into content blocks).
- ~~`read_comments`~~ not offered: GET /v2/blog/{blog-identifier}/notes ('Get notes for a specific Post') is at the OAuth level, so it needs a signed OAuth 1.0a request or an OAuth2 user token that the runtime cannot obtain or refresh (https://www.tumblr.com/docs/en/api/v2#notes---get-notes-for-a-specific-post).
- ~~`reply_comment`~~ not offered: The API documents no method that creates a reply note; replies are only made in the Tumblr apps (the v2 reference lists post creation, editing, reblogging and deletion, all at the OAuth level).
- ~~`read_mentions`~~ not offered: The API documents no mention feed; the closest, GET /v2/blog/{blog-identifier}/notifications ('Retrieve Blog's Activity Feed'), is an OAuth-level endpoint that the runtime cannot call without a user token (https://www.tumblr.com/docs/en/api/v2#notifications--retrieve-blogs-activity-feed).
- ~~`delete`~~ not offered: POST /v2/blog/{blog-identifier}/post/delete {id} is at the OAuth level ('Delete a Post', parameter `id`: 'The ID of the post to delete'); it needs a signed OAuth 1.0a request or an OAuth2 user token, which the runtime cannot obtain or refresh (https://www.tumblr.com/docs/en/api/v2#postdelete--delete-a-post).

## Credentials

- `PLATFORM_MCP_TUMBLR_API_KEY` — The OAuth Consumer Key of an app registered at https://www.tumblr.com/oauth/apps, sent as the `api_key` query parameter ('API key: Requires an API key. Use your OAuth Consumer Key as your api_key', https://www.tumblr.com/docs/en/api/v2#authentication). It only unlocks the public blog methods; everything at the 'OAuth' level (posting, notes, user info, deletion) needs a signed OAuth 1.0a request or an OAuth2 user token and is listed under not_offered.
- `PLATFORM_MCP_TUMBLR_BLOG_IDENTIFIER` — The blog to read, as its blog name (staff), hostname (staff.tumblr.com or a custom domain) or UUID (t:0aY0xL2Fi1OFJg4YxpmegQ) ('blog-identifier', https://www.tumblr.com/docs/en/api/v2#blog-identifiers); env PLATFORM_MCP_TUMBLR_BLOG_IDENTIFIER.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve tumblr   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve tumblr
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve tumblr   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/tumblr-mcp`. Python and TypeScript serve identical tools.
