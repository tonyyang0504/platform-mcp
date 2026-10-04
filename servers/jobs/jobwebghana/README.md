# Jobweb Ghana MCP server

Category: **jobs** · Docs: https://jobwebghana.com/feed/?post_type=job_listing · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/jobs/jobwebghana.json`; edit the catalog, not this file.

## Tools

- `search` — `GET /feed/` (https://jobwebghana.com/feed/?post_type=job_listing)
- ~~`me`~~ not offered: No credentials to verify ('auth: none'): the feed is public and has no account endpoint.
- ~~`get_posting`~~ not offered: The feed has no per-item endpoint (each posting's url is an HTML page); search returns the whole record in raw.
- ~~`apply`~~ not offered: No application endpoint: the feed only lists postings; candidates apply on each posting's url (employer page / e-mail).
- ~~`list_messages`~~ not offered: No messaging API; the only machine-readable interface is the public job feed.

## Credentials

None.

## Run

    uvx platform-mcp-hub serve jobwebghana          # Python
    npx -y platform-mcp-hub serve jobwebghana       # TypeScript
    claude mcp add jobwebghana -- uvx platform-mcp-hub serve jobwebghana

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/jobwebghana-mcp`. Python and TypeScript serve identical tools.
