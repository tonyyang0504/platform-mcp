# mobile.de MCP server

Category: **automotive** · Docs: https://services.mobile.de/docs/search-api.html · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/automotive/mobilede.json`; edit the catalog, not this file.

## Tools

- `search_listings` — `GET /search` (https://services.mobile.de/docs/search-api.html)
- `get_listing` — `GET /ad/{listing_id}` (https://services.mobile.de/docs/search-api.html)
- ~~`decode_vin`~~ not offered: The Search-API has no VIN lookup (vin is only a field of an ad).
- ~~`get_valuation`~~ not offered: Valuations are not part of the Search-API (the separate Insights-API is not covered here).
- ~~`list_dealers`~~ not offered: The Search-API filters by customerNumber/customerId but has no dealer directory endpoint.
- ~~`me`~~ not offered: No account/identity endpoint in the Search-API.

## Credentials

- `PLATFORM_MCP_MOBILEDE_USERNAME` — Username of a mobile.de API account (Search-API / Ad-Integration access is activated by mobile.de customer support); HTTP Basic.
- `PLATFORM_MCP_MOBILEDE_PASSWORD` — Password of that API account (HTTP Basic).

## Run

    uvx platform-mcp-hub serve mobilede          # Python
    npx -y platform-mcp-hub serve mobilede       # TypeScript
    claude mcp add mobilede -- uvx platform-mcp-hub serve mobilede

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/mobilede-mcp`. Python and TypeScript serve identical tools.
