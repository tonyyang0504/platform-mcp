# Telegram MCP server

Category: **social** · Docs: https://core.telegram.org/bots/api · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/social/telegram.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /getMe` (https://core.telegram.org/bots/api#getme)
- `publish_text` — `POST /sendMessage` (https://core.telegram.org/bots/api#sendmessage)
- `delete` — `POST /deleteMessage` (https://core.telegram.org/bots/api#deletemessage)
- `publish_image` — `POST /sendPhoto` (https://core.telegram.org/bots/api#sendphoto)
- ~~`read_comments`~~ not offered: The Bot API has no method that returns the messages or replies of a chat: comments on channel posts live in the linked discussion group and reach the bot only as updates through getUpdates or a webhook (https://core.telegram.org/bots/api#getting-updates).
- ~~`reply_comment`~~ not offered: A comment is a message in the channel's linked discussion group, a different chat from the configured chat_id; the bot cannot list comments (no read method) and sendMessage with reply_parameters needs that group's chat_id, which the vocabulary does not carry (https://core.telegram.org/bots/api#sendmessage).
- ~~`read_mentions`~~ not offered: No mention feed: mentions arrive only as `mention` / `text_mention` entities on incoming messages delivered through getUpdates or a webhook, and bots in groups see other messages only when privacy mode is off (https://core.telegram.org/bots/api#getting-updates).
- ~~`analytics_post`~~ not offered: The Bot API documents no per-message statistics method and its Message object carries no view or reaction counters; the only counter available to bots is getChatMemberCount for the whole chat (https://core.telegram.org/bots/api#available-methods).

## Credentials

- `PLATFORM_MCP_TELEGRAM_TOKEN` — Bot token from @BotFather. It is part of the URL path: 'All queries to the Telegram Bot API must be served over HTTPS and need to be presented in this form: https://api.telegram.org/bot<token>/METHOD_NAME' (https://core.telegram.org/bots/api#making-requests). The bot must be an administrator of the target channel with the right to post (and delete) messages. Same field as the messaging entry (env PLATFORM_MCP_TELEGRAM_TOKEN).
- `PLATFORM_MCP_TELEGRAM_CHAT_ID` — The channel (or group) the bot publishes to, sent as `chat_id`: 'Unique identifier for the target chat or username of the target channel (in the format @channelusername)', e.g. @mychannel or -1001234567890; env PLATFORM_MCP_TELEGRAM_CHAT_ID. Message ids are unique only inside this chat, so `post_id` values are message_ids of this chat.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve social/telegram   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve social/telegram
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve social/telegram   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/telegram-social-mcp`. Python and TypeScript serve identical tools.
