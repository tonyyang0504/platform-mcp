# We Work Remotely MCP server

Category: **deals** · Docs: https://weworkremotely.com/remote-jobs.rss · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/deals/we_work_remotely.json`; edit the catalog, not this file.

## Tools

- `search_postings` — `GET /remote-jobs.rss` (https://weworkremotely.com/remote-jobs.rss)
- ~~`me`~~ not offered: No credentials to verify ('auth: none'): the feed is public and has no account endpoint.
- ~~`get_posting`~~ not offered: The feed has no per-item endpoint; each posting's page (url) is HTML only. search_postings returns the whole record.
- ~~`submit_bid`~~ not offered: Applications go through the listing page on weworkremotely.com; there is no application API.
- ~~`withdraw_bid`~~ not offered: No bid API (see submit_bid).
- ~~`bid_status`~~ not offered: No bid API (see submit_bid).
- ~~`list_messages`~~ not offered: No messaging API; only the public feed is machine-readable.
- ~~`send_message`~~ not offered: No messaging API; only the public feed is machine-readable.
- ~~`credits`~~ not offered: No account or credit endpoint; the feed is keyless.

## Credentials

None.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve deals/we_work_remotely   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve deals/we_work_remotely
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve deals/we_work_remotely   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/we_work_remotely-deals-mcp`. Python and TypeScript serve identical tools.
