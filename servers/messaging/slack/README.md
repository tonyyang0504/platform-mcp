# Slack MCP server

Category: **messaging** · Docs: https://docs.slack.dev/ · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/messaging/slack.json`; edit the catalog, not this file.

## Tools

- `me` — `POST /auth.test` (https://docs.slack.dev/reference/methods/auth.test)
- `send` — `POST /chat.postMessage` (https://docs.slack.dev/reference/methods/chat.postMessage)
- `reply` — `POST /chat.postMessage` (https://docs.slack.dev/reference/methods/chat.postMessage)
- `get_thread` — `GET /conversations.replies` (https://docs.slack.dev/reference/methods/conversations.replies)
- `list_inbound` — `GET /conversations.history` (https://docs.slack.dev/reference/methods/conversations.history)
- `mark_read` — `POST /conversations.mark` (https://docs.slack.dev/reference/methods/conversations.mark)

## Credentials

- `PLATFORM_MCP_SLACK_TOKEN` — Bot token (xoxb-…) of an installed Slack app, sent as 'Authorization: Bearer' ('You must transmit your token as a bearer token in the Authorization HTTP header', https://docs.slack.dev/apis/web-api/). Scopes: chat:write (send, reply); channels:history, groups:history, im:history, mpim:history (list_inbound, get_thread); channels:manage, channels:write, groups:write, im:write or mpim:write (mark_read).

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve slack   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve slack
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve slack   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/slack-mcp`. Python and TypeScript serve identical tools.
