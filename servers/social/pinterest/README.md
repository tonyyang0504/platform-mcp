# Pinterest MCP server

Category: **social** · Docs: https://developers.pinterest.com/docs/api/v5/pins-create/ · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/social/pinterest.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /user_account` (https://developers.pinterest.com/docs/api/v5/user_account-get)
- `publish_image` — `POST /pins` (https://developers.pinterest.com/docs/api/v5/pins-create)
- `delete` — `DELETE /pins/{post_id}` (https://developers.pinterest.com/docs/api/v5/pins-delete)
- `analytics_post` — `GET /pins/{post_id}` (https://developers.pinterest.com/docs/api/v5/pins-get)
- ~~`publish_text`~~ not offered: A Pin always needs `media_source` (PinCreate requires media_source; https://developers.pinterest.com/docs/api/v5/pins-create).
- ~~`read_comments`~~ not offered: The v5 API has no comment endpoints (https://raw.githubusercontent.com/pinterest/api-description/main/v5/openapi.yaml).
- ~~`reply_comment`~~ not offered: The v5 API has no comment endpoints (https://raw.githubusercontent.com/pinterest/api-description/main/v5/openapi.yaml).
- ~~`read_mentions`~~ not offered: The v5 API has no mention or notification endpoint (https://raw.githubusercontent.com/pinterest/api-description/main/v5/openapi.yaml).

## Credentials

- `PLATFORM_MCP_PINTEREST_CLIENT_ID` — Pinterest app id; HTTP Basic username on POST https://api.pinterest.com/v5/oauth/token.
- `PLATFORM_MCP_PINTEREST_CLIENT_SECRET` — Pinterest app secret key; HTTP Basic password on the token request.
- `PLATFORM_MCP_PINTEREST_REFRESH_TOKEN` — Refresh token (pinr…) from the authorization-code flow with scopes user_accounts:read, boards:read, pins:read and pins:write. Continuous refresh tokens last 60 days and every refresh returns a new one: the runtime keeps it in memory and, with PLATFORM_MCP_STATE_DIR set, saves it to <dir>/pinterest.json (mode 0600).
- `PLATFORM_MCP_PINTEREST_BOARD_ID` — Board id new Pins are created on (GET /v5/boards).

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve social/pinterest   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve social/pinterest
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve social/pinterest   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/pinterest-social-mcp`. Python and TypeScript serve identical tools.
