# Get on Board MCP server

Category: **jobs** · Docs: https://www.getonbrd.com/api-doc.html · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/jobs/getonbrd.json`; edit the catalog, not this file.

## Tools

- `search` — `GET /api/v0/search/jobs` (https://www.getonbrd.com/api-doc.html)
- ~~`me`~~ not offered: No account endpoint for the public API; private endpoints use a company API key ('Company authentication for private endpoints').
- ~~`get_posting`~~ not offered: GET /api/v0/jobs/{id} is a private endpoint (security ApiKeyAuth: 'Send Authorization: Bearer <api_key>', answered 401 without one on 2026-09-24); the public search hit already carries the full description.
- ~~`apply`~~ not offered: POST /api/v0/applications is a company (ApiKeyAuth) endpoint for recruiters; candidates apply on getonbrd.com ('profile apply').
- ~~`list_messages`~~ not offered: No messaging API in the public API.

## Credentials

None.

## Run

    uvx platform-mcp-hub serve getonbrd          # Python
    npx -y platform-mcp-hub serve getonbrd       # TypeScript
    claude mcp add getonbrd -- uvx platform-mcp-hub serve getonbrd

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/getonbrd-mcp`. Python and TypeScript serve identical tools.
