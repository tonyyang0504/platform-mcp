# Working Nomads MCP server

Category: **deals** · Docs: https://www.workingnomads.com/api/exposed_jobs/ · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/deals/working_nomads.json`; edit the catalog, not this file.

## Tools

- `search_postings` — `GET /api/exposed_jobs/` (https://www.workingnomads.com/api/exposed_jobs/)
- ~~`submit_bid`~~ not offered: Page: 'no proposal / message / contract surface exists on this venue' — applicants use the posting's own application page.
- ~~`withdraw_bid`~~ not offered: No bid API (see submit_bid).
- ~~`bid_status`~~ not offered: No bid API (see submit_bid).
- ~~`list_messages`~~ not offered: No messaging API; the page documents the public listing feed only.
- ~~`send_message`~~ not offered: No messaging API; the page documents the public listing feed only.
- ~~`credits`~~ not offered: No account or credit endpoint; the feed is keyless.
- ~~`me`~~ not offered: No credentials to verify ('auth: none') and no account endpoint.
- ~~`get_posting`~~ not offered: No per-id endpoint is documented; re-read the record from the search hit (`url`).

## Credentials

None.

## Run

    uvx platform-mcp-hub serve deals/working_nomads          # Python
    npx -y platform-mcp-hub serve deals/working_nomads       # TypeScript
    claude mcp add working_nomads -- uvx platform-mcp-hub serve deals/working_nomads

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/working_nomads-deals-mcp`. Python and TypeScript serve identical tools.
