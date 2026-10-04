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

    uvx platform-mcp-hub serve usajobs          # Python
    npx -y platform-mcp-hub serve usajobs       # TypeScript
    claude mcp add usajobs -- uvx platform-mcp-hub serve usajobs

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/usajobs-mcp`. Python and TypeScript serve identical tools.
