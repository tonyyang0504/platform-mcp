# Discord MCP server

Category: **messaging** · Docs: https://docs.discord.com/developers/intro · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/messaging/discord.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /users/@me` (https://docs.discord.com/developers/resources/user#get-current-user)
- `send` — `POST /channels/{to}/messages` (https://docs.discord.com/developers/resources/message#create-message)
- `reply` — `POST /channels/{channel}/messages` (https://docs.discord.com/developers/resources/message#create-message)
- `list_inbound` — `GET /channels/{channel}/messages` (https://docs.discord.com/developers/resources/message#get-channel-messages)
- `get_thread` — `GET /channels/{thread_id}/messages` (https://docs.discord.com/developers/resources/message#get-channel-messages)
- ~~`mark_read`~~ not offered: Read state is a user-client concept; the bot-facing Channel and Message resources document no endpoint that marks a channel or message as read (https://docs.discord.com/developers/resources/channel, https://docs.discord.com/developers/resources/message).

## Credentials

- `PLATFORM_MCP_DISCORD_BOT_TOKEN` — Bot token from the app's Bot page in the Developer Portal, pasted WITHOUT the 'Bot ' prefix: the runtime adds it and sends 'Authorization: Bot <token>' ('authentication is performed with the Authorization HTTP header in the format Authorization: TOKEN_TYPE TOKEN', https://docs.discord.com/developers/reference#authentication). Channel permissions needed: VIEW_CHANNEL + READ_MESSAGE_HISTORY (list_inbound, get_thread), SEND_MESSAGES (send, reply); the MESSAGE_CONTENT privileged intent to read other users' message content.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve messaging/discord   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve messaging/discord
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve messaging/discord   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/discord-messaging-mcp`. Python and TypeScript serve identical tools.
