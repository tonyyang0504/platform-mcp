# Hot Nigerian Jobs MCP server

Category: **jobs** · Docs: https://www.hotnigerianjobs.com/feed/rss.xml · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/jobs/hotnigerianjobs.json`; edit the catalog, not this file.

## Tools

- `search` — `GET /feed/rss.xml` (https://www.hotnigerianjobs.com/feed/rss.xml)
- ~~`me`~~ not offered: No credentials to verify ('auth: none'): the feed is public and has no account endpoint.
- ~~`get_posting`~~ not offered: The feed has no per-item endpoint (each posting's url is an HTML page); search returns the whole record in raw.
- ~~`apply`~~ not offered: No application endpoint: the feed only lists postings; candidates apply on each posting's url (employer page / e-mail).
- ~~`list_messages`~~ not offered: No messaging API; the only machine-readable interface is the public job feed.

## Credentials

None.

## Run

    uvx platform-mcp-hub serve hotnigerianjobs          # Python
    npx -y platform-mcp-hub serve hotnigerianjobs       # TypeScript
    claude mcp add hotnigerianjobs -- uvx platform-mcp-hub serve hotnigerianjobs

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/hotnigerianjobs-mcp`. Python and TypeScript serve identical tools.
