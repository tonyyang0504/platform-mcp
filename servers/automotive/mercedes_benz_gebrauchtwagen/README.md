# Mercedes-Benz Vehicle Specification MCP server

Category: **automotive** · Docs: https://developer.mercedes-benz.com/products/vehicle_specification/docs · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/automotive/mercedes_benz_gebrauchtwagen.json`; edit the catalog, not this file.

## Tools

- `decode_vin` — `GET /vehicles/{vin}` (https://developer.mercedes-benz.com/products/vehicle_specification/docs)
- ~~`search_listings`~~ not offered: The Mercedes-Benz used-car locators have no public API; this OEM API only decodes VINs.
- ~~`get_listing`~~ not offered: No listing API (see search_listings).
- ~~`get_valuation`~~ not offered: No valuation in the Vehicle Specification API.
- ~~`list_dealers`~~ not offered: Not part of the Vehicle Specification API.
- ~~`me`~~ not offered: No identity endpoint for an API key.

## Credentials

- `PLATFORM_MCP_MERCEDES_BENZ_GEBRAUCHTWAGEN_API_KEY` — Secret API key of a Mercedes-Benz /developers console project subscribed to Vehicle Specification (commercial plan); sent as x-api-key.
- `PLATFORM_MCP_MERCEDES_BENZ_GEBRAUCHTWAGEN_LOCALE` — Market locale for descriptions, e.g. de_DE or en_GB (required by the API; only some locales are supported).

## Run

    uvx platform-mcp-hub serve mercedes_benz_gebrauchtwagen          # Python
    npx -y platform-mcp-hub serve mercedes_benz_gebrauchtwagen       # TypeScript
    claude mcp add mercedes_benz_gebrauchtwagen -- uvx platform-mcp-hub serve mercedes_benz_gebrauchtwagen

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/mercedes_benz_gebrauchtwagen-mcp`. Python and TypeScript serve identical tools.
