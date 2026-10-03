# Bilibili MCP server

Category: **social** · Docs: https://openhome.bilibili.com/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/social/bilibili.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /arcopen/fn/user/account/info` (https://open.bilibili.com/doc/4/feb66f99-7d87-c206-00e7-d84164cd701c)
- `delete` — `POST /arcopen/fn/archive/delete` (https://open.bilibili.com/doc/4/23d78390-4119-1e5f-2bbe-b45bd5cecdb0)
- `analytics_post` — `GET /arcopen/fn/data/arc/stat` (https://open.bilibili.com/doc/4/3f46ac2e-1318-3aa0-5548-0d9fd624d520)
- ~~`publish_text`~~ not offered: Bilibili's open platform publishes videos (服务端视频稿件投递: upload → chunk merge → submit) and 专栏 articles; 文章提交 (https://open.bilibili.com/doc/4/b14b77b6-8889-8c8b-2e83-17c5a4c550fb) requires title, category, template_id, a summary and 200–40000 characters of content, more than a text post carries.
- ~~`publish_image`~~ not offered: Images are only uploaded as article/cover material (专栏稿件图片上传, multipart file); there is no image-post API (https://open.bilibili.com/doc/4/0eaa4d3e-c4c0-f874-6f3c-e083aa939a1b).
- ~~`read_comments`~~ not offered: The open-platform document tree (https://member.bilibili.com/arcopen/user/open-doc/view?id=4) has no comment-reading API; 获取单个稿件数据 returns only the reply count.
- ~~`reply_comment`~~ not offered: No comment-reply API is documented in the open-platform tree (https://member.bilibili.com/arcopen/user/open-doc/view?id=4).
- ~~`read_mentions`~~ not offered: No mentions/@ API is documented in the open-platform tree (https://member.bilibili.com/arcopen/user/open-doc/view?id=4).

## Credentials

- `PLATFORM_MCP_BILIBILI_CLIENT_ID` — client_id of your Bilibili open-platform app (openhome.bilibili.com); also the x-bili-accesskeyid of every signed call.
- `PLATFORM_MCP_BILIBILI_CLIENT_SECRET` — The app secret (app_secret); signs every call (HMAC-SHA256) and is sent only to the refresh endpoint.
- `PLATFORM_MCP_BILIBILI_REFRESH_TOKEN` — The user's refresh_token from the OAuth2 code exchange (https://api.bilibili.com/x/account-oauth2/v1/token, scopes USER_INFO, ARC_BASE, ARC_DATA). Single-use: each refresh returns a new one that replaces it (persisted when PLATFORM_MCP_STATE_DIR is set).

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve bilibili   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve bilibili
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve bilibili   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/bilibili-mcp`. Python and TypeScript serve identical tools.
