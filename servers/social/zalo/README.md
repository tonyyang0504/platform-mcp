# Zalo MCP server

Category: **social** · Docs: https://developers.zalo.me/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/social/zalo.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /v2.0/oa/getoa` (https://stc-developers.zdn.vn/docs/v2/official-account/quan-ly/quan-ly-thong-tin-oa/lay-thong-tin-zalo-official-account)
- `publish_text` — `POST /v2.0/article/create` (https://stc-developers.zdn.vn/docs/v2/official-account/noi-dung/noi-dung-dang-bai-viet/)
- `publish_image` — `POST /v2.0/article/create` (https://stc-developers.zdn.vn/docs/v2/official-account/noi-dung/noi-dung-dang-bai-viet/)
- `delete` — `POST /v2.0/article/remove` (https://stc-developers.zdn.vn/docs/v2/official-account/noi-dung/noi-dung-dang-bai-viet/xoa-noi-dung-dang-bai-viet)
- ~~`read_comments`~~ not offered: The OA content APIs (https://stc-developers.zdn.vn/docs/v2/official-account/noi-dung/noi-dung-dang-bai-viet/: create, verify, getdetail, getslice, remove, update) expose no article comments.
- ~~`reply_comment`~~ not offered: No comment API exists for OA articles (https://stc-developers.zdn.vn/docs/v2/official-account/noi-dung/noi-dung-dang-bai-viet/).
- ~~`read_mentions`~~ not offered: The Official Account API has no mentions feed (https://developers.zalo.me/docs/official-account/noi-dung/tong-quan).
- ~~`analytics_post`~~ not offered: Per-article statistics are only total_view / total_share inside the paged list GET /v2.0/article/getslice (https://stc-developers.zdn.vn/docs/v2/official-account/noi-dung/noi-dung-dang-bai-viet/lay-danh-sach-noi-dung-dang-bai-viet), which cannot be filtered by id; GET /v2.0/article/getdetail returns no counts.

## Credentials

- `PLATFORM_MCP_ZALO_APP_ID` — ID of your Zalo app (developers.zalo.me > app > Thông tin ứng dụng).
- `PLATFORM_MCP_ZALO_SECRET_KEY` — The app's secret key (Khóa bí mật của ứng dụng); sent only as the secret_key header of the token request.
- `PLATFORM_MCP_ZALO_REFRESH_TOKEN` — OA refresh_token from the OA authorisation (POST https://oauth.zaloapp.com/v4/oa/access_token with grant_type=authorization_code). Valid 3 months and single-use: each refresh returns a new one that replaces it (persisted when PLATFORM_MCP_STATE_DIR is set). Access tokens last 25 h.
- `PLATFORM_MCP_ZALO_AUTHOR` — Author name shown on OA articles (≤50 characters).
- `PLATFORM_MCP_ZALO_COVER_PHOTO_URL` — URL of the cover photo used for text articles (the article API requires a cover).

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve social/zalo   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve social/zalo
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve social/zalo   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/zalo-social-mcp`. Python and TypeScript serve identical tools.
