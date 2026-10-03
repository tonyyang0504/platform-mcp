# Greenhouse MCP server

Category: **jobs** · Docs: https://developers.greenhouse.io/job-board.html · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/jobs/greenhouse.json`; edit the catalog, not this file.

## Tools

- `search` — `GET /boards/{board_token}/jobs` (https://developers.greenhouse.io/job-board.html#list-jobs)
- `get_posting` — `GET /boards/{board_token}/jobs/{id}` (https://developers.greenhouse.io/job-board.html#retrieve-a-job)
- ~~`me`~~ not offered: 'authentication is not required for any GET endpoints'; there is no account endpoint to verify.
- ~~`apply`~~ not offered: 'Only the application submission endpoint (POST https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs/{id}) requires Basic Auth' with the employer's Job Board API key, and resumes are multipart file uploads; candidates apply at absolute_url.
- ~~`list_messages`~~ not offered: No candidate messaging in the Job Board API.

## Credentials

- `PLATFORM_MCP_GREENHOUSE_BOARD_TOKEN` — The company's Greenhouse Job Board URL token, e.g. 'vaulttec' in https://boards.greenhouse.io/vaulttec.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve greenhouse   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve greenhouse
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve greenhouse   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/greenhouse-mcp`. Python and TypeScript serve identical tools.
