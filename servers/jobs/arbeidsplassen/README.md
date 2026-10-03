# Arbeidsplassen MCP server

Category: **jobs** · Docs: https://pam-stilling-feed.nav.no/swagger · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/jobs/arbeidsplassen.json`; edit the catalog, not this file.

## Tools

- `search` — `GET /api/v1/feed` (https://pam-stilling-feed.nav.no/swagger)
- `get_posting` — `GET /api/v1/feedentry/{id}` (https://pam-stilling-feed.nav.no/swagger)
- ~~`me`~~ not offered: No account endpoint: the OpenAPI lists /api/v1/feed, /api/v1/feed/{feedPageId} and /api/v1/feedentry/{entryId} only.
- ~~`apply`~~ not offered: Page: the API terms require deep-linking the job seeker to the source's application function (applicationUrl in raw); 'no apply API'.
- ~~`list_messages`~~ not offered: No messaging API; the OpenAPI documents the feed only.

## Credentials

- `PLATFORM_MCP_ARBEIDSPLASSEN_TOKEN` — JWT for NAV's job vacancy feed, sent as Authorization: Bearer. A rotating public token for experiments is served at GET https://pam-stilling-feed.nav.no/api/publicToken; a private one comes from nav.team.arbeidsplassen@nav.no after accepting the API terms (https://arbeidsplassen.nav.no/vilkar-api).

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve arbeidsplassen   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve arbeidsplassen
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve arbeidsplassen   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/arbeidsplassen-mcp`. Python and TypeScript serve identical tools.
