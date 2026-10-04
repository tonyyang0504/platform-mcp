# Instagram DM MCP server

Category: **messaging** · Docs: https://developers.facebook.com/docs/messenger-platform/instagram/features/send-message · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/messaging/instagram_dm.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /{page_id}` (https://developers.facebook.com/docs/graph-api/reference/page/)
- `list_inbound` — `GET /{page_id}/conversations` (https://developers.facebook.com/docs/messenger-platform/conversations)
- `get_thread` — `GET /{thread_id}/messages` (https://developers.facebook.com/docs/graph-api/reference/conversation/messages/)
- `send` — `POST /{page_id}/messages` (https://developers.facebook.com/docs/messenger-platform/instagram/features/send-message)
- ~~`reply`~~ not offered: Messages are addressed to a person: 'send a POST request to the /PAGE-ID/messages endpoint with the recipient parameter containing the Instagram-scoped ID (IGSID)' (https://developers.facebook.com/docs/messenger-platform/instagram/features/send-message); a conversation id cannot be a recipient. Use send with the IGSID (list_inbound from_id).
- ~~`mark_read`~~ not offered: The sender-action guide (https://developers.facebook.com/docs/messenger-platform/send-messages/sender-actions) documents mark_seen for Page-scoped IDs; the Instagram messaging pages read do not document a mark-as-read call for IGSIDs.

## Credentials

- `PLATFORM_MCP_INSTAGRAM_DM_PAGE_ACCESS_TOKEN` — Page access token of the Facebook Page linked to the Instagram professional account, requested by a person who can perform the MESSAGE task on that Page, with instagram_basic, instagram_manage_messages and pages_manage_metadata (Messenger Platform > Instagram Messaging, https://developers.facebook.com/docs/messenger-platform/instagram/features/send-message); sent as `Authorization: Bearer`.
- `PLATFORM_MCP_INSTAGRAM_DM_PAGE_ID` — Numeric id of the Facebook Page linked to the Instagram professional account; conversations are listed with /<page_id>/conversations?platform=instagram and messages sent with /<page_id>/messages. Env: PLATFORM_MCP_INSTAGRAM_DM_PAGE_ID.

## Run

    uvx platform-mcp-hub serve instagram_dm          # Python
    npx -y platform-mcp-hub serve instagram_dm       # TypeScript
    claude mcp add instagram_dm -- uvx platform-mcp-hub serve instagram_dm

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/instagram_dm-mcp`. Python and TypeScript serve identical tools.
