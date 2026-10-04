# Google Chat MCP server

Category: **messaging** · Docs: https://developers.google.com/workspace/chat · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/messaging/google_chat.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /spaces` (https://developers.google.com/workspace/chat/api/reference/rest/v1/spaces/list)
- `send` — `POST /spaces/{to}/messages` (https://developers.google.com/workspace/chat/api/reference/rest/v1/spaces.messages/create)
- `reply` — `POST /spaces/{channel}/messages` (https://developers.google.com/workspace/chat/api/reference/rest/v1/spaces.messages/create)
- `list_inbound` — `GET /spaces/{channel}/messages` (https://developers.google.com/workspace/chat/api/reference/rest/v1/spaces.messages/list)
- `get_thread` — `GET /spaces/{channel}/messages` (https://developers.google.com/workspace/chat/api/reference/rest/v1/spaces.messages/list)
- `mark_read` — `PATCH /users/me/spaces/{channel}/spaceReadState` (https://developers.google.com/workspace/chat/api/reference/rest/v1/users.spaces/updateSpaceReadState)

## Credentials

- `PLATFORM_MCP_GOOGLE_CHAT_CLIENT_ID` — OAuth 2.0 client id (Google Cloud console, Clients page) of the app the user consented to.
- `PLATFORM_MCP_GOOGLE_CHAT_CLIENT_SECRET` — The OAuth client's secret; sent with client_id, refresh_token and grant_type=refresh_token in the form body of POST https://oauth2.googleapis.com/token (https://developers.google.com/identity/protocols/oauth2/web-server#offline).
- `PLATFORM_MCP_GOOGLE_CHAT_REFRESH_TOKEN` — Refresh token from a one-time authorization-code consent with access_type=offline and the scopes https://www.googleapis.com/auth/chat.messages, chat.spaces.readonly and chat.users.readstate (user authentication; app authentication needs a service-account JWT, which this runtime does not sign). 'Refresh tokens are valid until the user revokes access or the refresh token expires'; the runtime mints 1-hour access tokens from it.

## Run

    uvx platform-mcp-hub serve google_chat          # Python
    npx -y platform-mcp-hub serve google_chat       # TypeScript
    claude mcp add google_chat -- uvx platform-mcp-hub serve google_chat

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/google_chat-mcp`. Python and TypeScript serve identical tools.
