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

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve gleif_lei   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve gleif_lei
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve gleif_lei   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/gleif_lei-mcp`. Python and TypeScript serve identical tools.
