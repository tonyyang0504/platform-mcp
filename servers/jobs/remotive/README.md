# Remotive MCP server

Category: **jobs** · Docs: https://github.com/remotive-com/remote-jobs-api · Verified: 2026-09-04

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/jobs/remotive.json`; edit the catalog, not this file.

## Tools

- `search` — `GET /remote-jobs` (https://github.com/remotive-com/remote-jobs-api)
- ~~`me`~~ not offered: No credentials to verify ('auth: none') and no account endpoint.
- ~~`get_posting`~~ not offered: Only the list endpoint and '/api/remote-jobs/categories' are documented; re-read the record from the search hit.
- ~~`apply`~~ not offered: Page: 'apply stays assist (url → Remotive → employer)'; robots.txt disallows /job/apply/*.
- ~~`list_messages`~~ not offered: No messaging API; the page documents job search and categories only.

## Credentials

None.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve jobs/remotive   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve jobs/remotive
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve jobs/remotive   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/remotive-jobs-mcp`. Python and TypeScript serve identical tools.
