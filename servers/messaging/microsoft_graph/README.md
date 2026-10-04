# Outlook / Microsoft 365 MCP server

Category: **messaging** · Docs: https://learn.microsoft.com/en-us/graph/api/resources/mail-api-overview · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/messaging/microsoft_graph.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /me` (https://learn.microsoft.com/en-us/graph/api/user-get?view=graph-rest-1.0)
- `list_inbound` — `GET /me/mailFolders/inbox/messages` (https://learn.microsoft.com/en-us/graph/api/user-list-messages?view=graph-rest-1.0)
- `get_thread` — `GET /me/messages` (https://learn.microsoft.com/en-us/graph/api/user-list-messages?view=graph-rest-1.0)
- `send` — `POST /me/sendMail` (https://learn.microsoft.com/en-us/graph/api/user-sendmail?view=graph-rest-1.0)
- `reply` — `POST /me/messages/{thread_id}/reply` (https://learn.microsoft.com/en-us/graph/api/message-reply?view=graph-rest-1.0)
- `mark_read` — `PATCH /me/messages/{message_id}` (https://learn.microsoft.com/en-us/graph/api/message-update?view=graph-rest-1.0)

## Credentials

- `PLATFORM_MCP_MICROSOFT_GRAPH_CLIENT_ID` — Application (client) ID of the Microsoft Entra app registration.
- `PLATFORM_MCP_MICROSOFT_GRAPH_CLIENT_SECRET` — Client secret of the app registration ('Only required for web apps'); leave empty for a public client. Sent in the form body of POST https://login.microsoftonline.com/common/oauth2/v2.0/token.
- `PLATFORM_MCP_MICROSOFT_GRAPH_REFRESH_TOKEN` — Refresh token from a one-time authorization-code consent including offline_access and the delegated scopes User.Read Mail.ReadWrite Mail.Send. Microsoft may return a new refresh token on every refresh; the runtime keeps it in memory and, with PLATFORM_MCP_STATE_DIR set, saves it to <dir>/<platform>.json (mode 0600).

## Run

    uvx platform-mcp-hub serve microsoft_graph          # Python
    npx -y platform-mcp-hub serve microsoft_graph       # TypeScript
    claude mcp add microsoft_graph -- uvx platform-mcp-hub serve microsoft_graph

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/microsoft_graph-mcp`. Python and TypeScript serve identical tools.
