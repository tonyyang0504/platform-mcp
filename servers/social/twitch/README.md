# Twitch MCP server

Category: **social** · Docs: https://dev.twitch.tv/docs/chat/ · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/social/twitch.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /users` (https://dev.twitch.tv/docs/api/reference/#get-users)
- `publish_text` — `POST /chat/messages` (https://dev.twitch.tv/docs/api/reference/#send-chat-message)
- `reply_comment` — `POST /chat/messages` (https://dev.twitch.tv/docs/api/reference/#send-chat-message)
- `delete` — `DELETE /moderation/chat?message_id={post_id}` (https://dev.twitch.tv/docs/api/reference/#delete-chat-messages)
- ~~`publish_image`~~ not offered: Chat messages are text and emotes only (Send Chat Message takes `message` text, https://dev.twitch.tv/docs/api/reference/#send-chat-message); there is no image upload.
- ~~`read_comments`~~ not offered: There is no REST endpoint to read chat; messages arrive through EventSub channel.chat.message (WebSocket or webhook, https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types/).
- ~~`read_mentions`~~ not offered: Mentions are only visible in the EventSub chat stream (https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types/); no REST feed exists.
- ~~`analytics_post`~~ not offered: Chat messages have no metrics endpoint; Helix analytics endpoints return CSV report URLs for extensions and games (https://dev.twitch.tv/docs/api/reference/#get-game-analytics).

## Credentials

- `PLATFORM_MCP_TWITCH_CLIENT_ID` — Twitch app client id (dev.twitch.tv console); also sent as the Client-Id header required on every Helix call.
- `PLATFORM_MCP_TWITCH_CLIENT_SECRET` — Twitch app client secret (form body of the refresh request to https://id.twitch.tv/oauth2/token).
- `PLATFORM_MCP_TWITCH_REFRESH_TOKEN` — User refresh token from the authorization-code flow with scopes user:write:chat and moderator:manage:chat_messages. 'Because refresh tokens may change, your app should safely store the new refresh token': the runtime keeps it in memory and, with PLATFORM_MCP_STATE_DIR set, saves it to <dir>/twitch.json (mode 0600).
- `PLATFORM_MCP_TWITCH_BROADCASTER_ID` — User id of the channel whose chat is used (GET /helix/users?login=…).
- `PLATFORM_MCP_TWITCH_SENDER_ID` — User id of the token's user (GET /helix/users with the token); sender of messages and moderator for delete.

## Run

    uvx platform-mcp-hub serve social/twitch          # Python
    npx -y platform-mcp-hub serve social/twitch       # TypeScript
    claude mcp add twitch -- uvx platform-mcp-hub serve social/twitch

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/twitch-social-mcp`. Python and TypeScript serve identical tools.
