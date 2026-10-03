# itch.io Help Wanted or Offered MCP server

Category: **deals** · Docs: https://itch.io/board/10020/help-wanted-or-offered · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/deals/itch_io_jobs.json`; edit the catalog, not this file.

## Tools

- `search_postings` — `GET /board/10020/help-wanted-or-offered.rss` (https://itch.io/board/10020/help-wanted-or-offered)
- ~~`me`~~ not offered: The itch.io server-side API key endpoints (credentials/info, me) belong to the separate game API, not this board feed; the feed is anonymous.
- ~~`get_posting`~~ not offered: The feed has no per-item endpoint; each posting's page (url) is HTML only. search_postings returns the whole record.
- ~~`submit_bid`~~ not offered: Replies are posted on the topic page with an itch.io account; the server-side API (https://itch.io/docs/api/serverside) has no community board endpoints.
- ~~`withdraw_bid`~~ not offered: No bid API (see submit_bid).
- ~~`bid_status`~~ not offered: No bid API (see submit_bid).
- ~~`list_messages`~~ not offered: No messaging API; only the public feed is machine-readable.
- ~~`send_message`~~ not offered: No messaging API; only the public feed is machine-readable.
- ~~`credits`~~ not offered: No account or credit endpoint; the feed is keyless.

## Credentials

None.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve itch_io_jobs   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve itch_io_jobs
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve itch_io_jobs   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/itch_io_jobs-mcp`. Python and TypeScript serve identical tools.
