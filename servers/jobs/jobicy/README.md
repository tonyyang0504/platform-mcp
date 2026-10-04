# Jobicy MCP server

Category: **jobs** · Docs: https://jobicy.com/jobs-rss-feed · Verified: 2026-09-04

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/jobs/jobicy.json`; edit the catalog, not this file.

## Tools

- `search` — `GET /remote-jobs` (https://jobicy.com/jobs-rss-feed)
- ~~`me`~~ not offered: No credentials to verify ('auth: none') and no account endpoint.
- ~~`get_posting`~~ not offered: Only the list endpoint (plus ?get=locations / ?get=industries) is documented; re-read the record from the search hit.
- ~~`apply`~~ not offered: Page: 'Apply stays assist (url → Jobicy listing → employer)'.
- ~~`list_messages`~~ not offered: No messaging API; the page documents job search, RSS and the value lists only.

## Credentials

None.

## Run

    uvx platform-mcp-hub serve jobs/jobicy          # Python
    npx -y platform-mcp-hub serve jobs/jobicy       # TypeScript
    claude mcp add jobicy -- uvx platform-mcp-hub serve jobs/jobicy

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/jobicy-jobs-mcp`. Python and TypeScript serve identical tools.
