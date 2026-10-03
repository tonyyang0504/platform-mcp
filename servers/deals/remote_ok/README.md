# Remote OK MCP server

Category: **deals** · Docs: https://remoteok.com/api · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/deals/remote_ok.json`; edit the catalog, not this file.

## Tools

- `search_postings` — `GET /api` (https://remoteok.com/api)
- ~~`submit_bid`~~ not offered: Page: 'no proposal / message / contract surface exists on this venue' — applicants use the posting's own application page (apply_url).
- ~~`withdraw_bid`~~ not offered: No bid API (see submit_bid).
- ~~`bid_status`~~ not offered: No bid API (see submit_bid).
- ~~`list_messages`~~ not offered: No messaging API; the page documents the public listing feed only.
- ~~`send_message`~~ not offered: No messaging API; the page documents the public listing feed only.
- ~~`credits`~~ not offered: No account or credit endpoint; the feed is keyless.
- ~~`me`~~ not offered: No credentials to verify ('auth: none') and no account endpoint.
- ~~`get_posting`~~ not offered: No per-id endpoint is documented; re-read the record from the search hit (`url` / `apply_url`).

## Credentials

None.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve deals/remote_ok   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve deals/remote_ok
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve deals/remote_ok   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/remote_ok-deals-mcp`. Python and TypeScript serve identical tools.
