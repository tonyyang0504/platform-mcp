# BloggingPro Job Board MCP server

Category: **deals** · Docs: https://www.bloggingpro.com/jobs/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/deals/bloggingpro_jobs.json`; edit the catalog, not this file.

## Tools

- `search_postings` — `GET /job-listings` (https://developer.wordpress.org/rest-api/reference/posts/#list-posts)
- `get_posting` — `GET /job-listings/{id}` (https://developer.wordpress.org/rest-api/reference/posts/#retrieve-a-post)
- ~~`me`~~ not offered: Anonymous read-only REST access; there is no account to verify without a WordPress login, which the board does not offer to API clients.
- ~~`submit_bid`~~ not offered: No application endpoint: each listing carries an external apply URL or e-mail (meta._application); candidates apply there.
- ~~`withdraw_bid`~~ not offered: No application endpoint (see submit_bid).
- ~~`bid_status`~~ not offered: No application endpoint (see submit_bid).
- ~~`list_messages`~~ not offered: No messaging in the REST routes (posts, taxonomies and media only).
- ~~`send_message`~~ not offered: No messaging in the REST routes (posts, taxonomies and media only).
- ~~`credits`~~ not offered: Free to read; no account, credit or balance endpoint.

## Credentials

None.

## Run

    uvx platform-mcp-hub serve bloggingpro_jobs          # Python
    npx -y platform-mcp-hub serve bloggingpro_jobs       # TypeScript
    claude mcp add bloggingpro_jobs -- uvx platform-mcp-hub serve bloggingpro_jobs

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/bloggingpro_jobs-mcp`. Python and TypeScript serve identical tools.
