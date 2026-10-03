# Messenger MCP server

Category: **messaging** · Docs: https://developers.facebook.com/docs/messenger-platform/send-messages · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/messaging/messenger.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /{page_id}` (https://developers.facebook.com/docs/graph-api/reference/page/)
- `list_inbound` — `GET /{page_id}/conversations` (https://developers.facebook.com/docs/messenger-platform/conversations)
- `get_thread` — `GET /{thread_id}/messages` (https://developers.facebook.com/docs/graph-api/reference/conversation/messages/)
- `send` — `POST /{page_id}/messages` (https://developers.facebook.com/docs/messenger-platform/send-messages)
- `mark_read` — `POST /{page_id}/messages` (https://developers.facebook.com/docs/messenger-platform/send-messages/sender-actions)
- ~~`reply`~~ not offered: The Send API addresses a person, not a conversation: 'Set the ID for a person receiving the message in the recipient object parameter' (PSID, user_ref or post/comment id - https://developers.facebook.com/docs/messenger-platform/send-messages); a conversation id cannot be a recipient. Use send with the PSID (list_inbound from_id).

## Credentials

- `PLATFORM_MCP_MESSENGER_PAGE_ACCESS_TOKEN` — Page access token requested by a person who can perform the MESSAGING (or MODERATE) task on the Page, with pages_messaging, pages_manage_metadata and pages_read_engagement (https://developers.facebook.com/docs/messenger-platform/conversations); sent as `Authorization: Bearer`.
- `PLATFORM_MCP_MESSENGER_PAGE_ID` — Numeric id of the Facebook Page whose Messenger inbox is used; every call goes to /<page_id>/... Env: PLATFORM_MCP_MESSENGER_PAGE_ID.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve messenger   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve messenger
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve messenger   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/messenger-mcp`. Python and TypeScript serve identical tools.
