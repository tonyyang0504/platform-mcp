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

    uvx platform-mcp-hub serve nhtsa_vpic          # Python
    npx -y platform-mcp-hub serve nhtsa_vpic       # TypeScript
    claude mcp add nhtsa_vpic -- uvx platform-mcp-hub serve nhtsa_vpic

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/nhtsa_vpic-mcp`. Python and TypeScript serve identical tools.
