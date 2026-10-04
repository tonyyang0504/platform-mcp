# Discord MCP server

Category: **social** · Docs: https://docs.discord.com/developers/intro · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/social/discord.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /users/@me` (https://docs.discord.com/developers/resources/user#get-current-user)
- `publish_text` — `POST /channels/{channel_id}/messages` (https://docs.discord.com/developers/resources/message#create-message)
- `read_comments` — `GET /channels/{post_id}/messages` (https://docs.discord.com/developers/resources/message#get-channel-messages)
- `reply_comment` — `POST /channels/{channel_id}/messages` (https://docs.discord.com/developers/resources/message#create-message)
- `delete` — `DELETE /channels/{channel_id}/messages/{post_id}` (https://docs.discord.com/developers/resources/message#delete-message)
- `publish_image` — `POST /channels/{channel_id}/messages` (https://docs.discord.com/developers/resources/message#create-message)
- ~~`read_mentions`~~ not offered: No REST mention feed exists for bots: mentions arrive only as Gateway MESSAGE_CREATE events over the WebSocket connection (https://docs.discord.com/developers/events/gateway-events#message-create), which the HTTP runtime does not hold.
- ~~`analytics_post`~~ not offered: Discord publishes no view / impression metrics for a message; Get Channel Message returns only a per-emoji `reactions` array ({count, emoji, ...}) and no aggregate counters (https://docs.discord.com/developers/resources/message#get-channel-message).

## Credentials

- `PLATFORM_MCP_DISCORD_BOT_TOKEN` — Bot token from the app's Bot page in the Developer Portal, pasted WITHOUT the 'Bot ' prefix: the runtime adds it and sends 'Authorization: Bot <token>' ('authentication is performed with the Authorization HTTP header in the format Authorization: TOKEN_TYPE TOKEN', https://docs.discord.com/developers/reference#authentication). Channel permissions needed: VIEW_CHANNEL + READ_MESSAGE_HISTORY (read_comments), SEND_MESSAGES (publish_text, reply_comment), MANAGE_MESSAGES to delete other users' messages; the MESSAGE_CONTENT privileged intent to read other users' message content. Same field as the messaging entry (env PLATFORM_MCP_DISCORD_BOT_TOKEN).
- `PLATFORM_MCP_DISCORD_CHANNEL_ID` — Snowflake id of the guild text / announcement channel (or forum-post thread) the bot publishes to (Discord client: User Settings > Advanced > Developer Mode, then right-click the channel > Copy Channel ID). The social vocabulary carries no channel argument, so publish_text, reply_comment and delete all address /channels/<channel_id>/messages; env PLATFORM_MCP_DISCORD_CHANNEL_ID.

## Run

    uvx platform-mcp-hub serve social/discord          # Python
    npx -y platform-mcp-hub serve social/discord       # TypeScript
    claude mcp add discord -- uvx platform-mcp-hub serve social/discord

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/discord-social-mcp`. Python and TypeScript serve identical tools.
