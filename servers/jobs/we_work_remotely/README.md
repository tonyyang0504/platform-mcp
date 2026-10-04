# We Work Remotely MCP server

Category: **jobs** · Docs: https://weworkremotely.com/remote-jobs.rss · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/jobs/we_work_remotely.json`; edit the catalog, not this file.

## Tools

- `search` — `GET /remote-jobs.rss` (https://weworkremotely.com/remote-jobs.rss)
- ~~`me`~~ not offered: No credentials to verify ('auth: none'): the feed is public and has no account endpoint.
- ~~`get_posting`~~ not offered: The feed has no per-item endpoint (each posting's url is an HTML page); search returns the whole record in raw.
- ~~`apply`~~ not offered: No application endpoint: the feed only lists postings; candidates apply on each posting's url (employer page / e-mail).
- ~~`list_messages`~~ not offered: No messaging API; the only machine-readable interface is the public job feed.

## Credentials

None.

## Run

    uvx platform-mcp-hub serve jobs/we_work_remotely          # Python
    npx -y platform-mcp-hub serve jobs/we_work_remotely       # TypeScript
    claude mcp add we_work_remotely -- uvx platform-mcp-hub serve jobs/we_work_remotely

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/we_work_remotely-jobs-mcp`. Python and TypeScript serve identical tools.
