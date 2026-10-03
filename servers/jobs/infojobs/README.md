# InfoJobs MCP server

Category: **jobs** · Docs: https://developer.infojobs.net/documentation/operation-list/index.xhtml · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/jobs/infojobs.json`; edit the catalog, not this file.

## Tools

- `search` — `GET /9/offer` (https://developer.infojobs.net/documentation/operation/offer-list-9.xhtml)
- `get_posting` — `GET /7/offer/{id}` (https://developer.infojobs.net/documentation/operation/offer-get-7.xhtml)
- ~~`me`~~ not offered: The app credentials identify the developer application only; candidate data (/candidate…) needs a user token from the InfoJobs OAuth authorization-code flow.
- ~~`apply`~~ not offered: Applying (POST /application with killer questions, CV and cover letter) needs an authenticated candidate's OAuth token with the my_applications scope, which basic app authentication cannot supply.
- ~~`list_messages`~~ not offered: No messaging API is documented.

## Credentials

- `PLATFORM_MCP_INFOJOBS_CLIENT_ID` — Client ID of an application registered at https://developer.infojobs.net/ ('App authentication is done via HTTP basic access authentication' with Client ID and Client secret).
- `PLATFORM_MCP_INFOJOBS_CLIENT_SECRET` — Client secret of the same InfoJobs application.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve infojobs   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve infojobs
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve infojobs   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/infojobs-mcp`. Python and TypeScript serve identical tools.
