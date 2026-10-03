# Brønnøysundregistrene MCP server

Category: **sales** · Docs: https://data.brreg.no/enhetsregisteret/api/dokumentasjon/no/index.html · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/sales/no_brreg.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /enheter` (https://data.brreg.no/enhetsregisteret/api/dokumentasjon/no/index.html)
- `search` — `GET /enheter` (https://data.brreg.no/enhetsregisteret/api/dokumentasjon/no/index.html)
- `get_company` — `GET /enheter/{id}` (https://data.brreg.no/enhetsregisteret/api/dokumentasjon/no/index.html)

## Credentials

None.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve no_brreg   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve no_brreg
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve no_brreg   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/no_brreg-mcp`. Python and TypeScript serve identical tools.
