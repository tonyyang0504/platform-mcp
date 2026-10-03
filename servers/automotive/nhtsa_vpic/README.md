# NHTSA vPIC (VIN decoder) MCP server

Category: **automotive** · Docs: https://vpic.nhtsa.dot.gov/api/ · Verified: 2026-09-27

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/automotive/nhtsa_vpic.json`; edit the catalog, not this file.

## Tools

- `decode_vin` — `GET /vehicles/DecodeVinValues/{vin}` (https://vpic.nhtsa.dot.gov/api/)
- ~~`me`~~ not offered: Public API without accounts or keys (https://vpic.nhtsa.dot.gov/api/).
- ~~`search_listings`~~ not offered: vPIC is a vehicle specification catalogue; it has no vehicle-for-sale listings.
- ~~`get_listing`~~ not offered: No listings in vPIC (specification data only).
- ~~`get_valuation`~~ not offered: vPIC publishes no prices or valuations.
- ~~`list_dealers`~~ not offered: vPIC lists manufacturers (GetAllManufacturers), not dealers.

## Credentials

None.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve nhtsa_vpic   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve nhtsa_vpic
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve nhtsa_vpic   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/nhtsa_vpic-mcp`. Python and TypeScript serve identical tools.
