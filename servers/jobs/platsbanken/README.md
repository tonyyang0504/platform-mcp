# Platsbanken MCP server

Category: **jobs** · Docs: https://jobtechdev.se/ · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/jobs/platsbanken.json`; edit the catalog, not this file.

## Tools

- `search` — `GET /search` (https://jobsearch.api.jobtechdev.se/)
- `get_posting` — `GET /ad/{id}` (https://jobsearch.api.jobtechdev.se/)
- ~~`me`~~ not offered: No credentials to verify ('auth: none') and no account endpoint in the Swagger.
- ~~`apply`~~ not offered: Page: 'apply to the employer' — ads carry application_details.url / email; there is no application endpoint.
- ~~`list_messages`~~ not offered: No messaging API; the Swagger documents search, complete, ad and logo only.

## Credentials

None.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve platsbanken   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve platsbanken
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve platsbanken   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/platsbanken-mcp`. Python and TypeScript serve identical tools.
