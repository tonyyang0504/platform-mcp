# Tradera MCP server

Category: **automotive** · Docs: https://api.tradera.com/documentation/rest-getting-started · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/automotive/tradera.json`; edit the catalog, not this file.

## Tools

- `get_listing` — `GET /items/{listing_id}` (https://api.tradera.com/documentation/rest/items)
- ~~`search_listings`~~ not offered: GET /v4/search exists (query, categoryId, pageNumber, orderBy), but its SearchResult schema in the published OpenAPI (https://api.tradera.com/v4/swagger/v4/swagger.json) is an empty object and the REST search page documents no response fields, so results cannot be mapped from evidence.
- ~~`decode_vin`~~ not offered: No VIN lookup in the Tradera API.
- ~~`get_valuation`~~ not offered: No valuation endpoint in the Tradera API.
- ~~`list_dealers`~~ not offered: No dealer directory endpoint in the Tradera API.
- ~~`me`~~ not offered: User endpoints need X-User-Id/X-User-Token from the token login flow; this adapter uses application credentials only.

## Credentials

- `PLATFORM_MCP_TRADERA_APP_ID` — Application ID (integer) of an app registered in the Tradera Developer Center (self-service).
- `PLATFORM_MCP_TRADERA_APP_KEY` — Application key (GUID) of that app. Read-only calls (search, items, categories) need only these two headers.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve tradera   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve tradera
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve tradera   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/tradera-mcp`. Python and TypeScript serve identical tools.
