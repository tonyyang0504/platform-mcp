# Intercom MCP server

Category: **messaging** · Docs: https://developers.intercom.com/ · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/messaging/intercom.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /me` (https://developers.intercom.com/docs/references/rest-api/api.intercom.io/admins/identifyadmin)
- `send` — `POST /messages` (https://developers.intercom.com/docs/references/rest-api/api.intercom.io/messages/createmessage)
- `reply` — `POST /conversations/{thread_id}/reply` (https://developers.intercom.com/docs/references/rest-api/api.intercom.io/conversations/replyconversation)
- `list_inbound` — `GET /conversations` (https://developers.intercom.com/docs/references/rest-api/api.intercom.io/conversations/listconversations)
- `get_thread` — `GET /conversations/{thread_id}` (https://developers.intercom.com/docs/references/rest-api/api.intercom.io/conversations/retrieveconversation)
- `mark_read` — `PUT /conversations/{thread_id}` (https://developers.intercom.com/docs/references/rest-api/api.intercom.io/conversations/updateconversation)

## Credentials

- `PLATFORM_MCP_INTERCOM_ACCESS_TOKEN` — Access Token of the app (Developer Hub > Configure > Authentication, or an OAuth install), sent as 'Authorization: Bearer <access_token>' (https://developers.intercom.com/docs/build-an-integration/learn-more/authentication). Workspaces hosted in the EU / AU are served from https://api.eu.intercom.io / https://api.au.intercom.io (OpenAPI servers list), which this server does not switch to.
- `PLATFORM_MCP_INTERCOM_ADMIN_ID` — Intercom id of the admin (teammate) who authors replies and outbound messages — 'admin_id: The id of the admin who is authoring the comment' (https://developers.intercom.com/docs/references/rest-api/api.intercom.io/conversations/replyconversation); GET /me (the `me` tool) shows the token's own admin id. Env: PLATFORM_MCP_INTERCOM_ADMIN_ID.

## Run

    uvx platform-mcp-hub serve intercom          # Python
    npx -y platform-mcp-hub serve intercom       # TypeScript
    claude mcp add intercom -- uvx platform-mcp-hub serve intercom

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/intercom-mcp`. Python and TypeScript serve identical tools.
