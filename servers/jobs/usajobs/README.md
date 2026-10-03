# USAJOBS MCP server

Category: **jobs** · Docs: https://developer.usajobs.gov/ · Verified: 2026-09-04

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/jobs/usajobs.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /api/Search` (https://developer.usajobs.gov/guides/authentication)
- `search` — `GET /api/Search` (https://developer.usajobs.gov/api-reference/get-api-search)
- `get_posting` — `GET /api/Search` (https://developer.usajobs.gov/api-reference/get-api-search)
- ~~`apply`~~ not offered: Page: 'not offered — candidates apply on usajobs.gov with a login.gov account' (ApplyURI is in raw).
- ~~`list_messages`~~ not offered: Page: 'apply / status / messaging' are 'not offered'.

## Credentials

- `PLATFORM_MCP_USAJOBS_API_KEY` — USAJOBS API key requested on https://developer.usajobs.gov/ (free); sent as the Authorization-Key header on every call.
- `PLATFORM_MCP_USAJOBS_EMAIL` — The e-mail address registered with the API key; USAJOBS requires it as the User-Agent header on every call.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve usajobs   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve usajobs
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve usajobs   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/usajobs-mcp`. Python and TypeScript serve identical tools.
