# Zendesk MCP server

Category: **messaging** · Docs: https://developer.zendesk.com/documentation/ · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/messaging/zendesk.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /users/me` (https://developer.zendesk.com/api-reference/ticketing/users/users/#show-self)
- `list_inbound` — `GET /tickets` (https://developer.zendesk.com/api-reference/ticketing/tickets/tickets/#list-tickets)
- `get_thread` — `GET /tickets/{thread_id}/comments` (https://developer.zendesk.com/api-reference/ticketing/tickets/ticket_comments/#list-comments)
- `send` — `POST /tickets` (https://developer.zendesk.com/api-reference/ticketing/tickets/tickets/#create-ticket)
- `reply` — `PUT /tickets/{thread_id}` (https://developer.zendesk.com/api-reference/ticketing/tickets/tickets/#update-ticket)
- ~~`mark_read`~~ not offered: Tickets and comments have no per-agent read state in the Ticketing API (https://developer.zendesk.com/api-reference/ticketing/tickets/tickets/); only ticket status can be changed.

## Credentials

- `PLATFORM_MCP_ZENDESK_EMAIL_TOKEN` — Agent email followed by /token, e.g. jdoe@example.com/token: API-token auth is Basic '{email_address}/token:{api_token}' (https://developer.zendesk.com/api-reference/introduction/security-and-auth/).
- `PLATFORM_MCP_ZENDESK_API_TOKEN` — API token from Admin Center > Apps and integrations > APIs > Zendesk API.
- `PLATFORM_MCP_ZENDESK_SUBDOMAIN` — Zendesk subdomain: the `acme` of acme.zendesk.com.

## Run

    uvx platform-mcp-hub serve zendesk          # Python
    npx -y platform-mcp-hub serve zendesk       # TypeScript
    claude mcp add zendesk -- uvx platform-mcp-hub serve zendesk

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/zendesk-mcp`. Python and TypeScript serve identical tools.
