# Autos TREFA MCP server

Category: **automotive** · Docs: https://autostrefa.mx/documentacion · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/automotive/autostrefa_mx.json`; edit the catalog, not this file.

## Tools

- `search_listings` — `GET /inventory` (https://autostrefa.mx/documentacion)
- `get_listing` — `GET /inventory/{listing_id}` (https://autostrefa.mx/documentacion)
- ~~`decode_vin`~~ not offered: No VIN endpoint in the public API.
- ~~`get_valuation`~~ not offered: No valuation endpoint (the MCP server's financing calculator is not a valuation).
- ~~`list_dealers`~~ not offered: TREFA is a single retailer; /inventory/stats aggregates the inventory but lists no dealers.
- ~~`me`~~ not offered: The public API has no authentication or account.

## Credentials

None.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve autostrefa_mx   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve autostrefa_mx
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve autostrefa_mx   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/autostrefa_mx-mcp`. Python and TypeScript serve identical tools.
