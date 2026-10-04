# Devpost MCP server

Category: **deals** · Docs: https://devpost.com/api/hackathons · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/deals/devpost.json`; edit the catalog, not this file.

## Tools

- `search_postings` — `GET /api/hackathons` (https://devpost.com/api/hackathons)
- ~~`submit_bid`~~ not offered: Page: 'No API for registration or submission — assist card with start_a_submission_url'; ToS forbids automated vote manipulation.
- ~~`withdraw_bid`~~ not offered: No bid API (see submit_bid).
- ~~`bid_status`~~ not offered: No bid API (see submit_bid).
- ~~`list_messages`~~ not offered: No messaging API; the page documents the public listing feed only.
- ~~`send_message`~~ not offered: No messaging API; the page documents the public listing feed only.
- ~~`credits`~~ not offered: No account or credit endpoint; the feed is keyless.
- ~~`me`~~ not offered: No credentials to verify ('auth: none') and no account endpoint.
- ~~`get_posting`~~ not offered: Details live on each hackathon's own site (HTML, 'not machine-readable'); re-read the record from the search hit.

## Credentials

None.

## Run

    uvx platform-mcp-hub serve devpost          # Python
    npx -y platform-mcp-hub serve devpost       # TypeScript
    claude mcp add devpost -- uvx platform-mcp-hub serve devpost

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/devpost-mcp`. Python and TypeScript serve identical tools.
