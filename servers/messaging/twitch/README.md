# Twitch MCP server

Category: **messaging** · Docs: https://dev.twitch.tv/docs · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/messaging/twitch.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /users` (https://dev.twitch.tv/docs/api/reference/#get-users)
- `send` — `POST /whispers` (https://dev.twitch.tv/docs/api/reference/#send-whisper)
- `reply` — `POST /chat/messages` (https://dev.twitch.tv/docs/api/reference/#send-chat-message)
- ~~`list_inbound`~~ not offered: Helix has no endpoint to read whispers or chat; they arrive only through EventSub (user.whisper.message, channel.chat.message; https://dev.twitch.tv/docs/eventsub/eventsub-subscription-types/).
- ~~`get_thread`~~ not offered: There is no whisper or chat history endpoint in Helix (https://dev.twitch.tv/docs/api/reference/); history exists only in EventSub deliveries.
- ~~`mark_read`~~ not offered: Twitch exposes no read-state for whispers or chat (https://dev.twitch.tv/docs/api/reference/).

## Credentials

- `PLATFORM_MCP_TWITCH_CLIENT_ID` — Twitch app client id (dev.twitch.tv console); also sent as the Client-Id header on every Helix call.
- `PLATFORM_MCP_TWITCH_CLIENT_SECRET` — Twitch app client secret (form body of the refresh request to https://id.twitch.tv/oauth2/token).
- `PLATFORM_MCP_TWITCH_REFRESH_TOKEN` — User refresh token from the authorization-code flow with scopes user:manage:whispers and user:write:chat. Twitch may return a new refresh token: the runtime keeps it in memory and, with PLATFORM_MCP_STATE_DIR set, saves it to <dir>/twitch.json (mode 0600). The state file is keyed by platform id, so it is shared with social/twitch: give each server its own PLATFORM_MCP_STATE_DIR (or its own consent / refresh token) so the two never race on one single-use refresh token.
- `PLATFORM_MCP_TWITCH_SENDER_ID` — User id of the token's user (GET /helix/users with the token): from_user_id of whispers and sender_id of chat replies. It 'must match the user ID in the user access token'; the account needs a verified phone number to whisper.
- `PLATFORM_MCP_TWITCH_BROADCASTER_ID` — User id of the channel whose chat reply posts into (needed only for reply).

## Run

    uvx platform-mcp-hub serve messaging/twitch          # Python
    npx -y platform-mcp-hub serve messaging/twitch       # TypeScript
    claude mcp add twitch -- uvx platform-mcp-hub serve messaging/twitch

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/twitch-messaging-mcp`. Python and TypeScript serve identical tools.
