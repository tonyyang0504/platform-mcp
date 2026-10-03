# SEOClerks MCP server

Category: **deals** · Docs: https://www.seoclerks.com/api/page/serviceads · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/deals/seoclerks.json`; edit the catalog, not this file.

## Tools

- `search_postings` — `GET /api` (https://www.seoclerks.com/api/page/serviceads)
- ~~`me`~~ not offered: Keyless API; no account endpoint.
- ~~`get_posting`~~ not offered: The API only selects lists of ads; there is no per-listing call. Re-read the record from the search hit (service_url opens the request).
- ~~`submit_bid`~~ not offered: No offer API; sellers respond to job requests on seoclerks.com while logged in.
- ~~`withdraw_bid`~~ not offered: No offer API (see submit_bid).
- ~~`bid_status`~~ not offered: No offer API (see submit_bid).
- ~~`list_messages`~~ not offered: No messaging API; the Service Ads API is read-only listings.
- ~~`send_message`~~ not offered: No messaging API; the Service Ads API is read-only listings.
- ~~`credits`~~ not offered: No account or balance endpoint.

## Credentials

None.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve seoclerks   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve seoclerks
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve seoclerks   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/seoclerks-mcp`. Python and TypeScript serve identical tools.
