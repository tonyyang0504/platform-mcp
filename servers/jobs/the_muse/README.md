# The Muse MCP server

Category: **jobs** · Docs: https://www.themuse.com/developers/api/v2 · Verified: 2026-09-04

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/jobs/the_muse.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /jobs` (https://www.themuse.com/developers/api/v2)
- `search` — `GET /jobs` (https://www.themuse.com/developers/api/v2)
- `get_posting` — `GET /jobs/{id}` (https://www.themuse.com/developers/api/v2)
- ~~`apply`~~ not offered: Page: 'not offered — refs.landing_page leads to The Muse job page, then the employer'.
- ~~`list_messages`~~ not offered: Page: 'apply / status / messaging' are 'not offered'.

## Credentials

- `PLATFORM_MCP_THE_MUSE_API_KEY` — Optional: register the app at https://www.themuse.com/developers/api/v2 to get an api_key (sent as the api_key query parameter), raising the limit from 500 to 3,600 requests/hour.

## Run

    uvx platform-mcp-hub serve the_muse          # Python
    npx -y platform-mcp-hub serve the_muse       # TypeScript
    claude mcp add the_muse -- uvx platform-mcp-hub serve the_muse

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/the_muse-mcp`. Python and TypeScript serve identical tools.
