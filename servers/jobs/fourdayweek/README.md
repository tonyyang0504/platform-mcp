# 4dayweek.io MCP server

Category: **jobs** · Docs: https://4dayweek.io/developers · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/jobs/fourdayweek.json`; edit the catalog, not this file.

## Tools

- `search` — `GET /api/v2/jobs` (https://4dayweek.io/developers)
- `get_posting` — `GET /api/v2/jobs/{id}` (https://4dayweek.io/developers)
- ~~`me`~~ not offered: No credentials to verify (no-auth API) and no account endpoint.
- ~~`apply`~~ not offered: Page: 'external apply' — postings link to the employer; 4dayweek's paid 'Auto Apply' is their product, not an API.
- ~~`list_messages`~~ not offered: No messaging API; the developer page documents the jobs endpoints and the RSS feed only.

## Credentials

None.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve fourdayweek   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve fourdayweek
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve fourdayweek   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/fourdayweek-mcp`. Python and TypeScript serve identical tools.
