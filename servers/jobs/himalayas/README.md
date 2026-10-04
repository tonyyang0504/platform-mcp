# Himalayas MCP server

Category: **jobs** · Docs: https://himalayas.app/api · Verified: 2026-09-04

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/jobs/himalayas.json`; edit the catalog, not this file.

## Tools

- `search` — `GET /jobs/api` (https://himalayas.app/api)
- ~~`me`~~ not offered: No credentials to verify ('auth: none') and no account endpoint.
- ~~`get_posting`~~ not offered: Only the feed endpoint is documented; re-read the record (id = guid) from the search hit.
- ~~`apply`~~ not offered: Page: 'apply stays assist (applicationLink → Himalayas / employer)'.
- ~~`list_messages`~~ not offered: No messaging API; the page documents the jobs feed only.

## Credentials

None.

## Run

    uvx platform-mcp-hub serve jobs/himalayas          # Python
    npx -y platform-mcp-hub serve jobs/himalayas       # TypeScript
    claude mcp add himalayas -- uvx platform-mcp-hub serve jobs/himalayas

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/himalayas-jobs-mcp`. Python and TypeScript serve identical tools.
