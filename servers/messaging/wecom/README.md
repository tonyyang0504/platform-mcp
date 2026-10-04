# WeCom (企业微信) MCP server

Category: **messaging** · Docs: https://developer.work.weixin.qq.com/document/ · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/messaging/wecom.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /agent/get` (https://developer.work.weixin.qq.com/document/path/90227)
- `send` — `POST /message/send` (https://developer.work.weixin.qq.com/document/path/90236)
- ~~`list_inbound`~~ not offered: Messages sent to an app arrive only on the encrypted XML callback URL (https://developer.work.weixin.qq.com/document/path/90238); kf/sync_msg covers only the separate 微信客服 (customer service) product.
- ~~`get_thread`~~ not offered: No conversation-history API exists for app messages: they are pushed to the app's callback URL only (https://developer.work.weixin.qq.com/document/path/90238); chat archiving (会话内容存档) is a separately licensed SDK product, not a REST call.
- ~~`reply`~~ not offered: App messages have no threads; reply with send to the member's UserID (https://developer.work.weixin.qq.com/document/path/90236).
- ~~`mark_read`~~ not offered: No read-state API for app messages (https://developer.work.weixin.qq.com/document/path/90236).

## Credentials

- `PLATFORM_MCP_WECOM_CORPID` — Enterprise ID (我的企业 > 企业信息), sent with corpsecret to GET https://qyapi.weixin.qq.com/cgi-bin/gettoken; the returned access_token (7200 s) travels as the access_token query parameter of every call.
- `PLATFORM_MCP_WECOM_CORPSECRET` — Secret of the self-built app (应用管理 > 应用 > Secret); each app has its own secret and token. Do not call gettoken frequently (rate-limited); the runtime caches the token.
- `PLATFORM_MCP_WECOM_AGENT_ID` — AgentId (integer) of the self-built app shown on its settings page; required by message/send and agent/get.

## Run

    uvx platform-mcp-hub serve wecom          # Python
    npx -y platform-mcp-hub serve wecom       # TypeScript
    claude mcp add wecom -- uvx platform-mcp-hub serve wecom

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/wecom-mcp`. Python and TypeScript serve identical tools.
