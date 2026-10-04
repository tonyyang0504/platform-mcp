# Working Nomads MCP server

Category: **jobs** · Docs: https://www.workingnomads.com/api/exposed_jobs/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/jobs/working_nomads.json`; edit the catalog, not this file.

## Tools

- `search` — `GET /api/exposed_jobs/` (https://www.workingnomads.com/api/exposed_jobs/)
- ~~`me`~~ not offered: No credentials to verify ('auth: none') and no account endpoint.
- ~~`get_posting`~~ not offered: No per-id endpoint is published; re-read the record from the search hit (url).
- ~~`apply`~~ not offered: No application endpoint; the posting url leads to the employer's application page.
- ~~`list_messages`~~ not offered: No messaging endpoint; only the public job feed is published.

## Credentials

None.

## Run

    uvx platform-mcp-hub serve jobs/working_nomads          # Python
    npx -y platform-mcp-hub serve jobs/working_nomads       # TypeScript
    claude mcp add working_nomads -- uvx platform-mcp-hub serve jobs/working_nomads

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/working_nomads-jobs-mcp`. Python and TypeScript serve identical tools.
