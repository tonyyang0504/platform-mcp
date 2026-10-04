# Gmail MCP server

Category: **messaging** · Docs: https://developers.google.com/workspace/gmail/api/guides · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/messaging/gmail.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /users/me/profile` (https://developers.google.com/workspace/gmail/api/reference/rest/v1/users/getProfile)
- `list_inbound` — `GET /users/me/messages` (https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/list)
- `get_thread` — `GET /users/me/threads/{thread_id}` (https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.threads/get)
- `mark_read` — `POST /users/me/messages/{message_id}/modify` (https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/modify)
- ~~`send`~~ not offered: users.messages.send takes a Message whose `raw` is 'The entire email message in an RFC 2822 formatted and base64url encoded string' — 'Gmail messages are sent as base64URL encoded strings within the raw field' (https://developers.google.com/workspace/gmail/api/guides/sending); the docs offer no JSON alternative and the adapter contract has no MIME/base64url encoding expression.
- ~~`reply`~~ not offered: Replies are also users.messages.send with a base64url RFC 2822 `raw` body plus threadId and matching References/In-Reply-To headers (https://developers.google.com/workspace/gmail/api/guides/sending); not expressible without a MIME encoding expression.

## Credentials

- `PLATFORM_MCP_GMAIL_CLIENT_ID` — OAuth 2.0 client id (Google Cloud console, Clients page) of the app the user consented to.
- `PLATFORM_MCP_GMAIL_CLIENT_SECRET` — The OAuth client's secret; sent with client_id, refresh_token and grant_type=refresh_token in the form body of POST https://oauth2.googleapis.com/token (https://developers.google.com/identity/protocols/oauth2/web-server#offline).
- `PLATFORM_MCP_GMAIL_REFRESH_TOKEN` — Refresh token from a one-time authorization-code consent with access_type=offline and the scopes https://www.googleapis.com/auth/gmail.modify (or gmail.readonly for reading only). 'Refresh tokens are valid until the user revokes access or the refresh token expires'; the runtime mints 1-hour access tokens from it.

## Run

    uvx platform-mcp-hub serve gmail          # Python
    npx -y platform-mcp-hub serve gmail       # TypeScript
    claude mcp add gmail -- uvx platform-mcp-hub serve gmail

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/gmail-mcp`. Python and TypeScript serve identical tools.
