# BOAMP MCP server

Category: **deals** · Docs: https://www.boamp.fr/pages/api-boamp/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/deals/boamp.json`; edit the catalog, not this file.

## Tools

- `search_postings` — `GET /records` (https://boamp-datadila.opendatasoft.com/api/explore/v2.1/swagger.json)
- `get_posting` — `GET /records` (https://boamp-datadila.opendatasoft.com/api/explore/v2.1/swagger.json)
- ~~`me`~~ not offered: Anonymous open-data API; no account to verify.
- ~~`submit_bid`~~ not offered: Read-only open-data API; tenders are submitted on the buyer's profile platform (raw.donnees/url_avis give the link).
- ~~`withdraw_bid`~~ not offered: Read-only open-data API (see submit_bid).
- ~~`bid_status`~~ not offered: Read-only open-data API (see submit_bid).
- ~~`list_messages`~~ not offered: No messaging; the Explore API only supports GET over datasets.
- ~~`send_message`~~ not offered: No messaging; 'Only the HTTP GET method is supported.'
- ~~`credits`~~ not offered: No account or credit endpoint; the quota is reported in X-RateLimit-* headers only.

## Credentials

None.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve boamp   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve boamp
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve boamp   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/boamp-mcp`. Python and TypeScript serve identical tools.
