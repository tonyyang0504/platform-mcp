# Reed MCP server

Category: **jobs** · Docs: https://www.reed.co.uk/developers/jobseeker · Verified: 2026-09-04

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/jobs/reed.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /search` (https://www.reed.co.uk/developers/jobseeker)
- `search` — `GET /search` (https://www.reed.co.uk/developers/jobseeker)
- `get_posting` — `GET /jobs/{id}` (https://www.reed.co.uk/developers/jobseeker)
- ~~`apply`~~ not offered: Reed's Jobseeker API has no application endpoint; candidates apply on reed.co.uk.
- ~~`list_messages`~~ not offered: No messaging API.

## Credentials

- `PLATFORM_MCP_REED_API_KEY` — Reed Jobseeker API key from https://www.reed.co.uk/developers/jobseeker; sent as the HTTP Basic user name with an empty password.

## Run

    uvx platform-mcp-hub serve reed          # Python
    npx -y platform-mcp-hub serve reed       # TypeScript
    claude mcp add reed -- uvx platform-mcp-hub serve reed

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/reed-mcp`. Python and TypeScript serve identical tools.
