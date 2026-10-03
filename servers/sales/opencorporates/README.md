# OpenCorporates MCP server

Category: **sales** · Docs: https://api.opencorporates.com/documentation/API-Reference · Verified: 2026-09-05

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/sales/opencorporates.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /account_status` (https://api.opencorporates.com/documentation/API-Reference)
- `search` — `GET /companies/search` (https://api.opencorporates.com/documentation/API-Reference)
- `get_company` — `GET /companies/{id}` (https://api.opencorporates.com/documentation/API-Reference)

## Credentials

- `PLATFORM_MCP_OPENCORPORATES_API_TOKEN` — OpenCorporates API token ('available from your account page on OpenCorporates'), sent as the api_token query parameter on every request.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve opencorporates   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve opencorporates
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve opencorporates   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/opencorporates-mcp`. Python and TypeScript serve identical tools.
