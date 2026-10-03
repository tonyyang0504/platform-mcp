# LINE MCP server

Category: **messaging** · Docs: https://developers.line.biz/en/docs/messaging-api/ · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/messaging/line.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /v2/bot/info` (https://developers.line.biz/en/reference/messaging-api/#get-bot-info)
- `send` — `POST /v2/bot/message/push` (https://developers.line.biz/en/reference/messaging-api/#send-push-message)
- ~~`reply`~~ not offered: POST /v2/bot/message/reply needs the single-use, short-lived `replyToken` of the webhook event being answered (not a conversation id); nothing in the reply input carries it (https://developers.line.biz/en/reference/messaging-api/#send-reply-message).
- ~~`list_inbound`~~ not offered: The Messaging API has no message-history endpoint: inbound messages are delivered only to the channel's webhook URL (https://developers.line.biz/en/reference/messaging-api/#webhooks).
- ~~`get_thread`~~ not offered: No conversation or history resource exists; only media content of a webhook-delivered message can be fetched (GET https://api-data.line.me/v2/bot/message/{messageId}/content, https://developers.line.biz/en/reference/messaging-api/#get-content).
- ~~`mark_read`~~ not offered: POST /v2/bot/chat/markAsRead requires a `markAsReadToken` delivered in the webhook event ('Tokens must be used by the bot that received them via Webhook'), which none of the mark_read inputs carries (https://developers.line.biz/en/reference/messaging-api/#mark-as-read).

## Credentials

- `PLATFORM_MCP_LINE_CHANNEL_ACCESS_TOKEN` — Channel access token of the Messaging API channel (long-lived token from the LINE Developers Console, or a short-lived / v2.1 token), sent as 'Authorization: Bearer {channel access token}' (securitySchemes Bearer 'Channel access token' in LINE's official OpenAPI description, https://github.com/line/line-openapi/blob/main/messaging-api.yml; https://developers.line.biz/en/reference/messaging-api/#send-push-message).

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve messaging/line   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve messaging/line
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve messaging/line   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/line-messaging-mcp`. Python and TypeScript serve identical tools.
