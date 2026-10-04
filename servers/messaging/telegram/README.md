# Telegram MCP server

Category: **messaging** · Docs: https://core.telegram.org/bots/api · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/messaging/telegram.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /getMe` (https://core.telegram.org/bots/api#getme)
- `send` — `POST /sendMessage` (https://core.telegram.org/bots/api#sendmessage)
- `list_inbound` — `GET /getUpdates` (https://core.telegram.org/bots/api#getupdates)
- ~~`reply`~~ not offered: sendMessage replies through `reply_parameters` ({message_id, chat_id, ...}), a nested object the adapter's flat body map cannot express (the former reply_to_message_id parameter is no longer in the sendMessage table, https://core.telegram.org/bots/api#sendmessage).
- ~~`get_thread`~~ not offered: The Bot API has no method that returns the messages of a chat or thread; inbound messages arrive only through getUpdates or a webhook (https://core.telegram.org/bots/api#getting-updates).
- ~~`mark_read`~~ not offered: No read-marking method exists in the Bot API (https://core.telegram.org/bots/api#available-methods).

## Credentials

- `PLATFORM_MCP_TELEGRAM_TOKEN` — Bot token from @BotFather. It is part of the URL path: 'All queries to the Telegram Bot API must be served over HTTPS and need to be presented in this form: https://api.telegram.org/bot<token>/METHOD_NAME' (https://core.telegram.org/bots/api#making-requests).

## Run

    uvx platform-mcp-hub serve messaging/telegram          # Python
    npx -y platform-mcp-hub serve messaging/telegram       # TypeScript
    claude mcp add telegram -- uvx platform-mcp-hub serve messaging/telegram

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/telegram-messaging-mcp`. Python and TypeScript serve identical tools.
