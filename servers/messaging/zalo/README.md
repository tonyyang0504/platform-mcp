# Zalo MCP server

Category: **messaging** · Docs: https://developers.zalo.me/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/messaging/zalo.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /v2.0/oa/getoa` (https://stc-developers.zdn.vn/docs/v2/official-account/quan-ly/quan-ly-thong-tin-oa/lay-thong-tin-zalo-official-account)
- `list_inbound` — `GET /v2.0/oa/listrecentchat` (https://stc-developers.zdn.vn/docs/v2/official-account/tin-nhan/quan-ly-tin-nhan/lay-thong-tin-tin-nhan-gan-nhat)
- `get_thread` — `GET /v2.0/oa/conversation` (https://stc-developers.zdn.vn/docs/v2/official-account/tin-nhan/quan-ly-tin-nhan/lay-thong-tin-tin-nhan-trong-mot-hoi-thoai)
- `send` — `POST /v3.0/oa/message/cs` (https://stc-developers.zdn.vn/docs/v2/official-account/tin-nhan/tin-tu-van/gui-tin-tu-van-dang-van-ban)
- `reply` — `POST /v3.0/oa/message/cs` (https://stc-developers.zdn.vn/docs/v2/official-account/tin-nhan/tin-tu-van/gui-tin-tu-van-dang-van-ban)
- ~~`mark_read`~~ not offered: The OA message-management APIs (https://stc-developers.zdn.vn/docs/v2/official-account/tin-nhan/quan-ly-tin-nhan/lay-thong-tin-tin-nhan-gan-nhat and siblings: recent chats, conversation, quota, uploads) have no mark-as-read call.

## Credentials

- `PLATFORM_MCP_ZALO_APP_ID` — ID of your Zalo app (developers.zalo.me > app > Thông tin ứng dụng).
- `PLATFORM_MCP_ZALO_SECRET_KEY` — The app's secret key (Khóa bí mật của ứng dụng); sent only as the secret_key header of the token request.
- `PLATFORM_MCP_ZALO_REFRESH_TOKEN` — OA refresh_token from the OA authorisation (POST https://oauth.zaloapp.com/v4/oa/access_token with grant_type=authorization_code). Valid 3 months and single-use: each refresh returns a new one that replaces it (persisted when PLATFORM_MCP_STATE_DIR is set). Access tokens last 25 h.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve messaging/zalo   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve messaging/zalo
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve messaging/zalo   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/zalo-messaging-mcp`. Python and TypeScript serve identical tools.
