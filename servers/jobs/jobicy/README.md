# Jobicy MCP server

Category: **jobs** · Docs: https://jobicy.com/jobs-rss-feed · Verified: 2026-09-04

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/jobs/jobicy.json`; edit the catalog, not this file.

## Tools

- `search` — `GET /remote-jobs` (https://jobicy.com/jobs-rss-feed)
- ~~`me`~~ not offered: No credentials to verify ('auth: none') and no account endpoint.
- ~~`get_posting`~~ not offered: Only the list endpoint (plus ?get=locations / ?get=industries) is documented; re-read the record from the search hit.
- ~~`apply`~~ not offered: Page: 'Apply stays assist (url → Jobicy listing → employer)'.
- ~~`list_messages`~~ not offered: No messaging API; the page documents job search, RSS and the value lists only.

## Credentials

None.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve jobs/jobicy   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve jobs/jobicy
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve jobs/jobicy   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/jobicy-jobs-mcp`. Python and TypeScript serve identical tools.
