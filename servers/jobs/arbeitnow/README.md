# Arbeitnow MCP server

Category: **jobs** · Docs: https://documenter.getpostman.com/view/18545278/UVJbJdKh · Verified: 2026-09-04

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/jobs/arbeitnow.json`; edit the catalog, not this file.

## Tools

- `search` — `GET /job-board-api` (https://www.arbeitnow.com/api/job-board-api)
- ~~`me`~~ not offered: No credentials to verify ('auth: none') and no account endpoint.
- ~~`get_posting`~~ not offered: Only the paginated feed is documented; re-read the record (id = slug) from the search hit.
- ~~`apply`~~ not offered: Page: 'apply stays assist (postings link to the employer)'; 'applying is on the employer's site'.
- ~~`list_messages`~~ not offered: No messaging API; the page documents the job feed only.

## Credentials

None.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve jobs/arbeitnow   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve jobs/arbeitnow
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve jobs/arbeitnow   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/arbeitnow-jobs-mcp`. Python and TypeScript serve identical tools.
