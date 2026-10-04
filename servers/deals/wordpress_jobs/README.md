# WordPress Jobs MCP server

Category: **deals** · Docs: https://jobs.wordpress.net/feed/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/deals/wordpress_jobs.json`; edit the catalog, not this file.

## Tools

- `search_postings` — `GET /feed/` (https://jobs.wordpress.net/feed/)
- ~~`me`~~ not offered: No credentials to verify ('auth: none'): the feed is public and has no account endpoint.
- ~~`get_posting`~~ not offered: The feed has no per-item endpoint; each posting's page (url) is HTML only. search_postings returns the whole record.
- ~~`submit_bid`~~ not offered: Each post lists how to apply (e-mail or link); the site has no application API and its REST index exposes no job type.
- ~~`withdraw_bid`~~ not offered: No bid API (see submit_bid).
- ~~`bid_status`~~ not offered: No bid API (see submit_bid).
- ~~`list_messages`~~ not offered: No messaging API; only the public feed is machine-readable.
- ~~`send_message`~~ not offered: No messaging API; only the public feed is machine-readable.
- ~~`credits`~~ not offered: No account or credit endpoint; the feed is keyless.

## Credentials

None.

## Run

    uvx platform-mcp-hub serve deals/wordpress_jobs          # Python
    npx -y platform-mcp-hub serve deals/wordpress_jobs       # TypeScript
    claude mcp add wordpress_jobs -- uvx platform-mcp-hub serve deals/wordpress_jobs

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/wordpress_jobs-deals-mcp`. Python and TypeScript serve identical tools.
