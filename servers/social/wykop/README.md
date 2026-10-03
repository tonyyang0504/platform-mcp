# Wykop MCP server

Category: **social** · Docs: https://doc.wykop.pl/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/social/wykop.json`; edit the catalog, not this file.

## Tools

- `read_comments` — `GET /entries/{post_id}/comments` (https://doc.wykop.pl/resources/entries/entries_comments.yaml)
- `analytics_post` — `GET /entries/{post_id}` (https://doc.wykop.pl/resources/entries/entries_entry.yaml)
- ~~`me`~~ not offered: Needs a user JWT: user sessions come from POST /refresh-token with a nested JSON body {data: {refresh_token}} that answers a NEW refresh_token every time ('otrzymujemy nowy token JWT oraz nowy refresh_token'); the runtime's session login cannot keep that rotated token and oauth2_refresh_token sends a flat grant_type=refresh_token body. Missing: a refresh-token grant with a nested JSON body and rotation read from data.refresh_token.
- ~~`publish_text`~~ not offered: POST /entries needs a user JWT (see me: rotating refresh token in a nested JSON body).
- ~~`publish_image`~~ not offered: Needs a user JWT (see me) and media are first uploaded through POST /media/photos (multipart upload or URL) before the entry.
- ~~`reply_comment`~~ not offered: POST /entries/{entryId}/comments needs a user JWT (see me).
- ~~`read_mentions`~~ not offered: Mentions are user notifications (GET /notifications/entries) and need a user JWT (see me).
- ~~`delete`~~ not offered: DELETE /entries/{entryId} needs a user JWT (see me).

## Credentials

- `PLATFORM_MCP_WYKOP_APP_KEY` — Wykop application key (appkey) issued for the app.
- `PLATFORM_MCP_WYKOP_APP_SECRET` — Secret paired with the app key.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve wykop   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve wykop
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve wykop   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/wykop-mcp`. Python and TypeScript serve identical tools.
