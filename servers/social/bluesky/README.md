# Bluesky MCP server

Category: **social** · Docs: https://docs.bsky.app/ · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/social/bluesky.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /xrpc/com.atproto.server.getSession` (https://raw.githubusercontent.com/bluesky-social/atproto/main/lexicons/com/atproto/server/getSession.json)
- `publish_text` — `POST /xrpc/com.atproto.repo.createRecord` (https://raw.githubusercontent.com/bluesky-social/atproto/main/lexicons/com/atproto/repo/createRecord.json)
- `read_comments` — `GET /xrpc/app.bsky.feed.getPostThread` (https://raw.githubusercontent.com/bluesky-social/atproto/main/lexicons/app/bsky/feed/getPostThread.json)
- `read_mentions` — `GET /xrpc/app.bsky.notification.listNotifications` (https://raw.githubusercontent.com/bluesky-social/atproto/main/lexicons/app/bsky/notification/listNotifications.json)
- `analytics_post` — `GET /xrpc/app.bsky.feed.getPosts` (https://raw.githubusercontent.com/bluesky-social/atproto/main/lexicons/app/bsky/feed/getPosts.json)
- ~~`publish_image`~~ not offered: Images must first be uploaded as raw bytes to POST /xrpc/com.atproto.repo.uploadBlob (<= 1 MB each) and embedded as app.bsky.embed.images; the runtime has no file upload.
- ~~`reply_comment`~~ not offered: A reply is a createRecord whose record.reply carries root and parent strong refs {uri, cid}; the cid of the comment (and of the thread root) must be fetched first via getPosts / getPostThread, and the runtime cannot chain calls.
- ~~`delete`~~ not offered: POST /xrpc/com.atproto.repo.deleteRecord needs {repo, collection, rkey}; the rkey is the last path segment of the post's AT-URI (at://did/app.bsky.feed.post/<rkey>) and the runtime has no expression to split it out of `post_id`.

## Credentials

- `PLATFORM_MCP_BLUESKY_IDENTIFIER` — Bluesky handle (e.g. alice.bsky.social) or the account's e-mail; sent as `identifier` to com.atproto.server.createSession.
- `PLATFORM_MCP_BLUESKY_PASSWORD` — An app password from Settings → Privacy and security → App Passwords, never the account password; the runtime exchanges it for a short-lived accessJwt (createSession is capped at 300/day per IP, so the token is cached and re-issued only on expiry or 401).
- `PLATFORM_MCP_BLUESKY_DID` — The account's DID (did:plc:..., shown in Settings → Account or returned by com.atproto.server.getSession); used as `repo` when writing records. The createRecord lexicon also accepts the handle here.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve bluesky   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve bluesky
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve bluesky   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/bluesky-mcp`. Python and TypeScript serve identical tools.
