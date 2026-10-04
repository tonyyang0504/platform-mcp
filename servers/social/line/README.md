# LINE MCP server

Category: **social** · Docs: https://developers.line.biz/en/docs/messaging-api/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/social/line.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /v2/bot/info` (https://developers.line.biz/en/reference/messaging-api/#get-bot-info)
- `publish_text` — `POST /v2/bot/message/broadcast` (https://developers.line.biz/en/reference/messaging-api/#send-broadcast-message)
- `publish_image` — `POST /v2/bot/message/broadcast` (https://developers.line.biz/en/reference/messaging-api/#image-message)
- `analytics_post` — `GET /v2/bot/insight/message/event` (https://developers.line.biz/en/reference/messaging-api/#get-message-event)
- ~~`read_comments`~~ not offered: Broadcasts have no comments: user replies arrive only as webhook events to the channel's webhook URL (https://developers.line.biz/en/reference/messaging-api/#webhooks); there is no message-history endpoint.
- ~~`reply_comment`~~ not offered: POST /v2/bot/message/reply needs the short-lived single-use `replyToken` of a webhook event, not a comment id (https://developers.line.biz/en/reference/messaging-api/#send-reply-message).
- ~~`read_mentions`~~ not offered: Group mentions are delivered only inside webhook message events (mention.mentionees, https://developers.line.biz/en/reference/messaging-api/#wh-text); no REST feed exists.
- ~~`delete`~~ not offered: A sent message cannot be recalled: the Messaging API reference (https://github.com/line/line-openapi/blob/main/messaging-api.yml) defines no delete / unsend operation for messages.

## Credentials

- `PLATFORM_MCP_LINE_CHANNEL_ACCESS_TOKEN` — Channel access token of the LINE Official Account's Messaging API channel (long-lived token from the LINE Developers Console, or a v2.1 token), sent as 'Authorization: Bearer {channel access token}' (securitySchemes Bearer in https://github.com/line/line-openapi/blob/main/messaging-api.yml).

## Run

    uvx platform-mcp-hub serve social/line          # Python
    npx -y platform-mcp-hub serve social/line       # TypeScript
    claude mcp add line -- uvx platform-mcp-hub serve social/line

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/line-social-mcp`. Python and TypeScript serve identical tools.
