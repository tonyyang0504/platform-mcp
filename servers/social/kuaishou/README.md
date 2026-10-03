# Kuaishou MCP server

Category: **social** · Docs: https://open.kuaishou.com/platform/openApi?menu=13 · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/social/kuaishou.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /openapi/user_info` (https://open.kuaishou.com/platform/openApi?menu=17)
- `delete` — `POST /openapi/photo/delete` (https://open.kuaishou.com/platform/openApi?menu=21)
- `analytics_post` — `GET /openapi/photo/info` (https://open.kuaishou.com/platform/openApi?menu=22)
- ~~`publish_text`~~ not offered: Kuaishou's content API publishes videos only (视频发布, https://open.kuaishou.com/platform/openApi?menu=20: start_upload → binary/multipart upload → publish); there is no text post.
- ~~`publish_image`~~ not offered: Only video works can be published (https://open.kuaishou.com/platform/openApi?menu=20), via a binary or multipart file upload; no image-by-URL post exists.
- ~~`read_comments`~~ not offered: The 内容管理 APIs (https://open.kuaishou.com/platform/openApi?menu=22) return comment_count only; no comment list endpoint is documented.
- ~~`reply_comment`~~ not offered: No comment API is documented in the Kuaishou Open Platform content-management section (https://open.kuaishou.com/platform/openApi?menu=22).
- ~~`read_mentions`~~ not offered: No mentions API is documented (https://open.kuaishou.com/platform/openApi?menu=22).

## Credentials

- `PLATFORM_MCP_KUAISHOU_APP_ID` — app_id of your Kuaishou Open Platform application (https://open.kuaishou.com/platform).
- `PLATFORM_MCP_KUAISHOU_APP_SECRET` — app_secret of the same application; sent only to /oauth2/refresh_token.
- `PLATFORM_MCP_KUAISHOU_REFRESH_TOKEN` — The user's refresh_token from the 快手登录 authorization-code exchange (/oauth2/access_token, scopes user_info, user_video_info, user_video_delete; valid 180 days). It is single-use: every refresh returns a new one that replaces it (persisted when PLATFORM_MCP_STATE_DIR is set; 'refreshToken.discarded' means an old one was reused).

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve kuaishou   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve kuaishou
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve kuaishou   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/kuaishou-mcp`. Python and TypeScript serve identical tools.
