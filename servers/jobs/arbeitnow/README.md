# Arbeitnow MCP server

Category: **jobs** · Docs: https://documenter.getpostman.com/view/18545278/UVJbJdKh · Verified: 2026-09-04

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/jobs/arbeitnow.json`; edit the catalog, not this file.

## Tools

- `search` — `GET /job-board-api` (https://www.arbeitnow.com/api/job-board-api)
- ~~`me`~~ not offered: No credentials to verify ('auth: none') and no account endpoint.
- ~~`get_posting`~~ not offered: Only the paginated feed is documented; re-read the record (id = slug) from the search hit.
- ~~`apply`~~ not offered: Page: 'apply stays assist (postings link to the employer)'; 'applying is on the employer's site'.
- ~~`list_messages`~~ not offered: No messaging API; the page documents the job feed only.

## Credentials

None.

## Run

    uvx platform-mcp-hub serve jobs/arbeitnow          # Python
    npx -y platform-mcp-hub serve jobs/arbeitnow       # TypeScript
    claude mcp add arbeitnow -- uvx platform-mcp-hub serve jobs/arbeitnow

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/arbeitnow-jobs-mcp`. Python and TypeScript serve identical tools.
