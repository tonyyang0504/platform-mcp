# YouTube MCP server

Category: **social** · Docs: https://developers.google.com/youtube/v3/docs/videos/insert · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/social/youtube.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /channels` (https://developers.google.com/youtube/v3/docs/channels/list)
- `read_comments` — `GET /commentThreads` (https://developers.google.com/youtube/v3/docs/commentThreads/list)
- `reply_comment` — `POST /comments` (https://developers.google.com/youtube/v3/docs/comments/insert)
- `delete` — `DELETE /videos` (https://developers.google.com/youtube/v3/docs/videos/delete)
- `analytics_post` — `GET /videos` (https://developers.google.com/youtube/v3/docs/videos/list)
- ~~`publish_text`~~ not offered: Community posts have no Data API method; the only publish method is videos.insert (https://developers.google.com/youtube/v3/docs/videos/insert).
- ~~`publish_image`~~ not offered: Images are only thumbnails: thumbnails.set is a media upload ('POST https://www.googleapis.com/upload/youtube/v3/thumbnails/set', https://developers.google.com/youtube/v3/docs/thumbnails/set) and videos.insert is a multipart/resumable upload; the runtime sends JSON bodies only.
- ~~`read_mentions`~~ not offered: No mention feed exists; search.list on a name is only a keyword search (https://developers.google.com/youtube/v3/docs/search/list).

## Credentials

- `PLATFORM_MCP_YOUTUBE_CLIENT_ID` — OAuth 2.0 client id (Google Cloud console, Clients page) of the app the user consented to.
- `PLATFORM_MCP_YOUTUBE_CLIENT_SECRET` — The OAuth client's secret; sent with client_id, refresh_token and grant_type=refresh_token in the form body of POST https://oauth2.googleapis.com/token (https://developers.google.com/identity/protocols/oauth2/web-server#offline).
- `PLATFORM_MCP_YOUTUBE_REFRESH_TOKEN` — Refresh token from a one-time authorization-code consent with access_type=offline and the scopes https://www.googleapis.com/auth/youtube.force-ssl. 'Refresh tokens are valid until the user revokes access or the refresh token expires'; the runtime mints 1-hour access tokens from it.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve youtube   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve youtube
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve youtube   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/youtube-mcp`. Python and TypeScript serve identical tools.
