# Viber MCP server

Category: **messaging** · Docs: https://developers.viber.com/docs/api/rest-bot-api/ · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/messaging/viber.json`; edit the catalog, not this file.

## Tools

- `me` — `POST /get_account_info` (https://developers.viber.com/docs/api/rest-bot-api/#get-account-info)
- `send` — `POST /send_message` (https://developers.viber.com/docs/api/rest-bot-api/#send-message)
- ~~`list_inbound`~~ not offered: Inbound messages arrive only as callbacks to the webhook set with set_webhook ('This webhook will be used for receiving callbacks and user messages from Viber', https://developers.viber.com/docs/api/rest-bot-api/#webhooks); there is no polling endpoint.
- ~~`get_thread`~~ not offered: No conversation history endpoint exists; messages reach the bot only through webhook callbacks (https://developers.viber.com/docs/api/rest-bot-api/#callbacks).
- ~~`reply`~~ not offered: The REST Bot API has no reply/thread parameter on send_message (https://developers.viber.com/docs/api/rest-bot-api/#send-message); use send to the same user.
- ~~`mark_read`~~ not offered: Read state exists only as incoming `seen` callbacks (https://developers.viber.com/docs/api/rest-bot-api/#callbacks); a bot cannot mark messages read.

## Credentials

- `PLATFORM_MCP_VIBER_AUTH_TOKEN` — Bot authentication token ('Each API request must include an HTTP Header called X-Viber-Auth-Token containing the account's authentication token'), shown in the bot's edit-info screen / Viber Admin Panel.
- `PLATFORM_MCP_VIBER_SENDER_NAME` — sender.name shown with every message ('required. Max 28 characters').

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve messaging/viber   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve messaging/viber
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve messaging/viber   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/viber-messaging-mcp`. Python and TypeScript serve identical tools.
