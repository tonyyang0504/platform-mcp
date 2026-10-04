# Microsoft Teams MCP server

Category: **messaging** · Docs: https://learn.microsoft.com/en-us/microsoftteams/platform/ · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/messaging/teams.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /me` (https://learn.microsoft.com/en-us/graph/api/user-get?view=graph-rest-1.0)
- `send` — `POST /chats/{to}/messages` (https://learn.microsoft.com/en-us/graph/api/chat-post-messages?view=graph-rest-1.0)
- `list_inbound` — `GET /chats/{channel}/messages` (https://learn.microsoft.com/en-us/graph/api/chat-list-messages?view=graph-rest-1.0)
- `get_thread` — `GET /teams/{team_id}/channels/{channel}/messages/{thread_id}/replies` (https://learn.microsoft.com/en-us/graph/api/chatmessage-list-replies?view=graph-rest-1.0)
- `reply` — `POST /teams/{team_id}/channels/{channel}/messages/{thread_id}/replies` (https://learn.microsoft.com/en-us/graph/api/chatmessage-post-replies?view=graph-rest-1.0)
- `mark_read` — `POST /chats/{channel}/markChatReadForUser` (https://learn.microsoft.com/en-us/graph/api/chat-markchatreadforuser?view=graph-rest-1.0)

## Credentials

- `PLATFORM_MCP_TEAMS_CLIENT_ID` — Application (client) ID of the Microsoft Entra app registration.
- `PLATFORM_MCP_TEAMS_CLIENT_SECRET` — Client secret of the app registration ('Only required for web apps'); leave empty for a public client. Sent in the form body of POST https://login.microsoftonline.com/common/oauth2/v2.0/token.
- `PLATFORM_MCP_TEAMS_REFRESH_TOKEN` — Refresh token from a one-time authorization-code consent including offline_access and the delegated scopes User.Read Chat.ReadWrite ChatMessage.Send ChannelMessage.Send ChannelMessage.Read.All (work or school accounts only; personal accounts are 'Not supported'). Microsoft may return a new refresh token on every refresh; the runtime keeps it in memory and, with PLATFORM_MCP_STATE_DIR set, saves it to <dir>/<platform>.json (mode 0600).
- `PLATFORM_MCP_TEAMS_TEAM_ID` — Team id whose channel threads get_thread and reply use (GET /me/joinedTeams).
- `PLATFORM_MCP_TEAMS_USER_ID` — Entra object id of the signed-in user (GET /me → id); required by mark_read.
- `PLATFORM_MCP_TEAMS_TENANT_ID` — Tenant id of the signed-in user; required by mark_read.

## Run

    uvx platform-mcp-hub serve teams          # Python
    npx -y platform-mcp-hub serve teams       # TypeScript
    claude mcp add teams -- uvx platform-mcp-hub serve teams

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/teams-mcp`. Python and TypeScript serve identical tools.
