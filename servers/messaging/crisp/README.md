# Crisp MCP server

Category: **messaging** · Docs: https://docs.crisp.chat/ · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/messaging/crisp.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /website/{website_id}` (https://docs.crisp.chat/references/rest-api/v1/#get-a-website)
- `list_inbound` — `GET /website/{website_id}/conversations/{page_number}` (https://docs.crisp.chat/references/rest-api/v1/#list-conversations)
- `get_thread` — `GET /website/{website_id}/conversation/{thread_id}/messages` (https://docs.crisp.chat/references/rest-api/v1/#get-messages-in-conversation)
- `reply` — `POST /website/{website_id}/conversation/{thread_id}/message` (https://docs.crisp.chat/references/rest-api/v1/#send-a-message-in-conversation)
- `mark_read` — `PATCH /website/{website_id}/conversation/{thread_id}/read` (https://docs.crisp.chat/references/rest-api/v1/#mark-messages-as-read-in-conversation)
- ~~`send`~~ not offered: A new conversation must first be created with POST /website/{website_id}/conversation (returns the session_id) and the recipient attached with PATCH .../conversation/{session_id}/meta before a message can be posted — chained calls the adapter cannot express, and `to` (an email) has no place in the message call (https://docs.crisp.chat/references/rest-api/v1/#create-a-new-conversation, https://docs.crisp.chat/references/rest-api/v1/#send-a-message-in-conversation).

## Credentials

- `PLATFORM_MCP_CRISP_IDENTIFIER` — Identifier half of the Crisp token keypair (plugin token from the Marketplace, or a website token), sent as the HTTP Basic username — 'Authorization: Basic BASE64(identifier:key)' (https://docs.crisp.chat/guides/rest-api/authentication/plugin-token/, https://docs.crisp.chat/guides/rest-api/authentication/website-token/).
- `PLATFORM_MCP_CRISP_KEY` — Key half of the Crisp token keypair, sent as the HTTP Basic password ('--user "{identifier}:{key}"' in the official curl examples).
- `PLATFORM_MCP_CRISP_WEBSITE_ID` — Crisp website (workspace) identifier that prefixes every route (/website/{website_id}/...). Env: PLATFORM_MCP_CRISP_WEBSITE_ID.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve crisp   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve crisp
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve crisp   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/crisp-mcp`. Python and TypeScript serve identical tools.
