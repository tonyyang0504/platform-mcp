# Himalayas MCP server

Category: **deals** · Docs: https://himalayas.app/jobs/api · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/deals/himalayas.json`; edit the catalog, not this file.

## Tools

- `search_postings` — `GET /jobs/api/search` (https://himalayas.app/api)
- ~~`me`~~ not offered: Keyless public API; no account endpoint.
- ~~`get_posting`~~ not offered: Only the browse feed (/jobs/api) and search (/jobs/api/search) are documented; there is no per-job endpoint — re-read the record (id = guid) from the search hit.
- ~~`submit_bid`~~ not offered: No application API; candidates apply at applicationLink (Himalayas or the employer).
- ~~`withdraw_bid`~~ not offered: No application API (see submit_bid).
- ~~`bid_status`~~ not offered: No application API (see submit_bid).
- ~~`list_messages`~~ not offered: No messaging API; the page documents the jobs feed and search only.
- ~~`send_message`~~ not offered: No messaging API; the page documents the jobs feed and search only.
- ~~`credits`~~ not offered: Free API; no account or credit endpoint.

## Credentials

None.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve deals/himalayas   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve deals/himalayas
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve deals/himalayas   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/himalayas-deals-mcp`. Python and TypeScript serve identical tools.
