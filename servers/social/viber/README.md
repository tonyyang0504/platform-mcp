# Viber MCP server

Category: **social** · Docs: https://developers.viber.com/docs/api/rest-bot-api/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/social/viber.json`; edit the catalog, not this file.

## Tools

- `me` — `POST /get_account_info` (https://developers.viber.com/docs/tools/channels-post-api/#get-account-info)
- `publish_text` — `POST /post` (https://developers.viber.com/docs/tools/channels-post-api/#text-message)
- `publish_image` — `POST /post` (https://developers.viber.com/docs/tools/channels-post-api/#picture-message)
- ~~`read_comments`~~ not offered: The Channels Post API only posts: 'Posting to the Channel using the API, or when new messages are posted in the Channel by users will not generate a callback to this webhook', and no read endpoint is documented (https://developers.viber.com/docs/tools/channels-post-api/).
- ~~`reply_comment`~~ not offered: No reply or comment parameter exists on /pa/post; the documented message types are text, picture, video, file, location, contact, sticker, url (https://developers.viber.com/docs/tools/channels-post-api/#message-types).
- ~~`read_mentions`~~ not offered: No mentions or notifications endpoint is documented for channels (https://developers.viber.com/docs/tools/channels-post-api/).
- ~~`delete`~~ not offered: No delete / unsend endpoint is documented for channel posts (https://developers.viber.com/docs/tools/channels-post-api/).
- ~~`analytics_post`~~ not offered: No statistics endpoint is documented for channel posts (https://developers.viber.com/docs/tools/channels-post-api/).

## Credentials

- `PLATFORM_MCP_VIBER_AUTH_TOKEN` — Viber Channel authentication token: as the channel's super admin open the Channel info screen > Developer Tools > copy token. The Channels Post API takes it as the auth_token member of every JSON request body (https://developers.viber.com/docs/tools/channels-post-api/). A webhook must have been set once with set_webhook before posting works (status 10 webhookNotSet otherwise).
- `PLATFORM_MCP_VIBER_SENDER_ID` — Viber user id of a Channel SUPER ADMIN, sent as `from` ('Only the superadmins' ID should be used as the sender ID with this API'); listed under members[] with role superadmin in get_account_info.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve social/viber   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve social/viber
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve social/viber   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/viber-social-mcp`. Python and TypeScript serve identical tools.
