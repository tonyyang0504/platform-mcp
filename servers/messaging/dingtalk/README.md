# DingTalk (钉钉) MCP server

Category: **messaging** · Docs: https://open.dingtalk.com/document/ · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/messaging/dingtalk.json`; edit the catalog, not this file.

## Tools

- `send` — `POST /v1.0/robot/oToMessages/batchSend` (https://open.dingtalk.com/document/orgapp/chatbots-send-one-on-one-chat-messages-in-batches)
- ~~`me`~~ not offered: No identity endpoint exists for an app accessToken; the token call itself (POST /v1.0/oauth2/accessToken, https://open.dingtalk.com/document/orgapp/obtain-the-access_token-of-an-internal-app) is the only credential check.
- ~~`list_inbound`~~ not offered: Messages to a robot are delivered only to the robot's callback (Stream mode or HTTP) (https://open.dingtalk.com/document/orgapp/robot-overview); there is no inbox poll.
- ~~`get_thread`~~ not offered: No conversation-history endpoint for robot chats (https://open.dingtalk.com/document/orgapp/robot-overview).
- ~~`reply`~~ not offered: Robot one-to-one chats have no threads; inbound callbacks carry a short-lived sessionWebhook instead (https://open.dingtalk.com/document/orgapp/robot-overview). Use send to the same userId.
- ~~`mark_read`~~ not offered: A robot can only query whether its own messages were read (POST /v1.0/robot/oToMessages/readStatus); it cannot mark messages read (https://open.dingtalk.com/document/orgapp/chatbot-batch-query-the-read-status-of-messages).

## Credentials

- `PLATFORM_MCP_DINGTALK_APP_KEY` — Client ID (formerly AppKey) of the internal enterprise app that owns the robot; exchanged at POST https://api.dingtalk.com/v1.0/oauth2/accessToken for a 7200-second accessToken.
- `PLATFORM_MCP_DINGTALK_APP_SECRET` — Client Secret (formerly AppSecret) of the same app (developer console, 凭证与基础信息).
- `PLATFORM_MCP_DINGTALK_ROBOT_CODE` — robotCode of the internal-app robot (developer console robot page; usually equals the app key).

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve dingtalk   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve dingtalk
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve dingtalk   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/dingtalk-mcp`. Python and TypeScript serve identical tools.
