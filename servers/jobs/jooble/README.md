# Jooble MCP server

Category: **jobs** · Docs: https://jooble.org/api/about · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/jobs/jooble.json`; edit the catalog, not this file.

## Tools

- `search` — `POST /{api_key}` (https://help.jooble.org/en/support/solutions/articles/60001448238-rest-api-documentation)
- ~~`me`~~ not offered: No account endpoint: the REST API documents a single search call whose key travels in the URL path.
- ~~`get_posting`~~ not offered: The REST API documents only the search call; there is no per-id endpoint — the search hit's link opens the posting on the source board.
- ~~`apply`~~ not offered: Aggregator: 'apply goes to the origin board'; no application API is documented.
- ~~`list_messages`~~ not offered: No messaging API; the documentation covers the search call only.

## Credentials

- `PLATFORM_MCP_JOOBLE_API_KEY` — Jooble REST API key issued after the request form on https://jooble.org/api/about; it is the last path segment of every call (POST https://jooble.org/api/{api_Key}). Each Jooble country domain has its own key; the free plan is limited to 500 requests per key in total.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve jooble   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve jooble
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve jooble   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/jooble-mcp`. Python and TypeScript serve identical tools.
