# Divar MCP server

Category: **automotive** · Docs: https://kenar.divar.dev/post/search_post · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/automotive/divar.json`; edit the catalog, not this file.

## Tools

- `search_listings` — `POST /v2/open-platform/finder/post` (https://kenar.divar.dev/post/search_post)
- `get_listing` — `GET /v1/open-platform/finder/post/{listing_id}` (https://kenar.divar.dev/post/get_post)
- ~~`decode_vin`~~ not offered: No VIN lookup in the Kenar API.
- ~~`get_valuation`~~ not offered: No valuation endpoint in the Kenar API.
- ~~`list_dealers`~~ not offered: No dealer directory endpoint in the Kenar API.
- ~~`me`~~ not offered: User endpoints need an OAuth grant from a Divar user; this adapter uses the app API key.

## Credentials

- `PLATFORM_MCP_DIVAR_API_KEY` — API key of a Kenar app (https://kenar.divar.dev/management/api-keys); search needs the SEARCH_POST permission.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve divar   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve divar
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve divar   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/divar-mcp`. Python and TypeScript serve identical tools.
