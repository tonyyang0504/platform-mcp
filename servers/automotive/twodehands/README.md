# 2dehands MCP server

Category: **automotive** · Docs: https://api.marktplaats.nl/docs/v1/overview.html · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/automotive/twodehands.json`; edit the catalog, not this file.

## Tools

- `search_listings` — `GET /v1/search` (https://api.marktplaats.nl/docs/v1/search-advertisements.html)
- `get_listing` — `GET /v1/advertisements/{listing_id}` (https://api.marktplaats.nl/docs/v1/advertisement.html)
- ~~`decode_vin`~~ not offered: No VIN lookup in the Marktplaats API.
- ~~`get_valuation`~~ not offered: No valuation endpoint in the Marktplaats API.
- ~~`list_dealers`~~ not offered: No dealer directory endpoint (only users/{id} for a known seller).
- ~~`me`~~ not offered: GET /v1/me needs a user token from the authorization-code flow; this adapter uses a client token.

## Credentials

- `PLATFORM_MCP_TWODEHANDS_CLIENT_ID` — Client id assigned by 2dehands (API clients are registered by the platform for business/advertiser use); grant_type=client_credentials at https://auth.2dehands.be/accounts/oauth/token.
- `PLATFORM_MCP_TWODEHANDS_CLIENT_SECRET` — Client secret assigned with it. A client token reaches public resources (categories, search, advertisements) only.
- `PLATFORM_MCP_TWODEHANDS_CATEGORY_ID` — Category id to restrict searches to (e.g. the cars category id from GET /v1/categories); without it `query` is mandatory.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve twodehands   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve twodehands
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve twodehands   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/twodehands-mcp`. Python and TypeScript serve identical tools.
