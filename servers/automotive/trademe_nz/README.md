# Trade Me Motors MCP server

Category: **automotive** · Docs: https://developer.trademe.co.nz/api-reference/search-methods/used-motors-search · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/automotive/trademe_nz.json`; edit the catalog, not this file.

## Tools

- `search_listings` — `GET /Search/Motors/Used.json` (https://developer.trademe.co.nz/api-reference/search-methods/used-motors-search)
- `get_listing` — `GET /Listings/{listing_id}.json` (https://developer.trademe.co.nz/api-reference/listing-methods/retrieve-the-details-of-a-single-listing)
- ~~`decode_vin`~~ not offered: No VIN lookup in the Trade Me API reference (MotorWeb reports are seller-purchased extras on a listing).
- ~~`get_valuation`~~ not offered: No valuation method in the Trade Me API reference.
- ~~`list_dealers`~~ not offered: No dealer directory method for motors in the Trade Me API reference.
- ~~`me`~~ not offered: Member endpoints (/v1/MyTradeMe/Summary) need a member access token from the OAuth 1.0a flow; this adapter signs as the application only.

## Credentials

- `PLATFORM_MCP_TRADEME_NZ_CONSUMER_KEY` — Trade Me API consumer key of your registered application (My Trade Me → Developer options; API access is granted after Trade Me reviews the application).
- `PLATFORM_MCP_TRADEME_NZ_CONSUMER_SECRET` — The application's consumer secret: sent as the OAuth 1.0a PLAINTEXT signature '<consumer secret>&' over HTTPS (Trade Me's documented PLAINTEXT workflow).

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve automotive/trademe_nz   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve automotive/trademe_nz
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve automotive/trademe_nz   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/trademe_nz-automotive-mcp`. Python and TypeScript serve identical tools.
