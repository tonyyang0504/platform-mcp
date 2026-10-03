# Mastodon MCP server

Category: **social** · Docs: https://docs.joinmastodon.org/methods/statuses/ · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/social/mastodon.json`; edit the catalog, not this file.

## Tools

- `me` — `GET https://{instance}/api/v1/accounts/verify_credentials` (https://docs.joinmastodon.org/methods/accounts/#verify_credentials)
- `publish_text` — `POST https://{instance}/api/v1/statuses` (https://docs.joinmastodon.org/methods/statuses/#create)
- `read_comments` — `GET https://{instance}/api/v1/statuses/{post_id}/context` (https://docs.joinmastodon.org/methods/statuses/#context)
- `reply_comment` — `POST https://{instance}/api/v1/statuses` (https://docs.joinmastodon.org/methods/statuses/#create)
- `read_mentions` — `GET https://{instance}/api/v1/notifications` (https://docs.joinmastodon.org/methods/notifications/#get)
- `analytics_post` — `GET https://{instance}/api/v1/statuses/{post_id}` (https://docs.joinmastodon.org/methods/statuses/#get)
- `delete` — `DELETE https://{instance}/api/v1/statuses/{post_id}` (https://docs.joinmastodon.org/methods/statuses/#delete)
- ~~`publish_image`~~ not offered: Images must first be uploaded as multipart files to POST /api/v2/media (then media_ids[] on the status); the runtime has no file upload.

## Credentials

- `PLATFORM_MCP_MASTODON_TOKEN` — Mastodon user access token from the account's instance (Preferences > Development > New application, or an OAuth flow) with scopes read:accounts read:statuses read:notifications write:statuses; sent as `Authorization: Bearer`.
- `PLATFORM_MCP_MASTODON_INSTANCE` — Host of the account's Mastodon instance without scheme, e.g. mastodon.social; every call goes to https://<instance>/api/v1/...

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve mastodon   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve mastodon
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve mastodon   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/mastodon-mcp`. Python and TypeScript serve identical tools.
