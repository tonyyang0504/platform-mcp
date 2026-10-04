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

    uvx platform-mcp-hub serve opencorporates          # Python
    npx -y platform-mcp-hub serve opencorporates       # TypeScript
    claude mcp add opencorporates -- uvx platform-mcp-hub serve opencorporates

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/opencorporates-mcp`. Python and TypeScript serve identical tools.
