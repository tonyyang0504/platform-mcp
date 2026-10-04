# GLEIF LEI records MCP server

Category: **sales** · Docs: https://www.gleif.org/en/lei-data/gleif-api · Verified: 2026-09-05

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/sales/gleif_lei.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /lei-records` (https://api.gleif.org/docs)
- `search` — `GET /lei-records` (https://api.gleif.org/docs)
- `get_company` — `GET /lei-records/{id}` (https://api.gleif.org/docs)

## Credentials

None.

## Run

    uvx platform-mcp-hub serve gleif_lei          # Python
    npx -y platform-mcp-hub serve gleif_lei       # TypeScript
    claude mcp add gleif_lei -- uvx platform-mcp-hub serve gleif_lei

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/gleif_lei-mcp`. Python and TypeScript serve identical tools.
