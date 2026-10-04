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

    uvx platform-mcp-hub serve hackernews          # Python
    npx -y platform-mcp-hub serve hackernews       # TypeScript
    claude mcp add hackernews -- uvx platform-mcp-hub serve hackernews

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/hackernews-mcp`. Python and TypeScript serve identical tools.
