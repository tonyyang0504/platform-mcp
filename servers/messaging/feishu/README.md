# Feishu / Lark MCP server

Category: **messaging** · Docs: https://open.feishu.cn/document/ · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/messaging/feishu.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /bot/v3/info` (https://open.feishu.cn/document/client-docs/bot-v3/obtain-bot-info)
- `list_inbound` — `GET /im/v1/messages` (https://open.feishu.cn/document/server-docs/im-v1/message/list)
- `get_thread` — `GET /im/v1/messages` (https://open.feishu.cn/document/server-docs/im-v1/message/list)
- `send` — `POST /im/v1/messages` (https://open.feishu.cn/document/server-docs/im-v1/message/create)
- `reply` — `POST /im/v1/messages/{thread_id}/reply` (https://open.feishu.cn/document/server-docs/im-v1/message/reply)
- ~~`mark_read`~~ not offered: There is no API for a bot to mark messages read; read receipts are only queryable (https://open.feishu.cn/document/server-docs/im-v1/message/read_users).

## Credentials

- `PLATFORM_MCP_FEISHU_APP_ID` — App ID of a Feishu custom (self-built) app with the bot capability (cli_…); exchanged with app_secret at POST /open-apis/auth/v3/tenant_access_token/internal for a tenant_access_token (max 2 hours).
- `PLATFORM_MCP_FEISHU_APP_SECRET` — App Secret of the same app (developer console, Credentials & Basic Info).
- `PLATFORM_MCP_FEISHU_RECEIVE_ID_TYPE` — How `send`'s `to` is interpreted (receive_id_type query parameter): chat_id (group or p2p chat oc_…, the usual choice), open_id, union_id, user_id or email. Set it to chat_id unless you address users directly.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve feishu   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve feishu
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve feishu   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/feishu-mcp`. Python and TypeScript serve identical tools.
