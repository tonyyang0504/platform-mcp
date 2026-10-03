# Hacker News MCP server

Category: **social** · Docs: https://github.com/HackerNews/API · Verified: 2026-09-02

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/social/hackernews.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /maxitem.json` (https://github.com/HackerNews/API)
- `analytics_post` — `GET /item/{post_id}.json` (https://github.com/HackerNews/API)
- ~~`publish_text`~~ not offered: Hacker News has no write API (submitting, commenting and voting are human-only per the guidelines).
- ~~`publish_image`~~ not offered: No write API.
- ~~`reply_comment`~~ not offered: No write API.
- ~~`delete`~~ not offered: No write API.
- ~~`read_comments`~~ not offered: GET /v0/item/{id}.json returns only comment ids in `kids`; each comment is a further GET /v0/item/{kid}.json and the runtime has no id-list fan-out (needs_runtime).
- ~~`read_mentions`~~ not offered: The official API has no search or mention endpoint (hn.algolia.com is third-party).

## Credentials

None.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve hackernews   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve hackernews
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve hackernews   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/hackernews-mcp`. Python and TypeScript serve identical tools.
