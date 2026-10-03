# Jobgether MCP server

Category: **jobs** · Docs: https://jobgether.com/developers · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/jobs/jobgether.json`; edit the catalog, not this file.

## Tools

- `search` — `GET /api/v1/jobs` (https://jobgether.com/developers)
- ~~`me`~~ not offered: No credentials to verify ('No API key No signup') and no account endpoint.
- ~~`get_posting`~~ not offered: The OpenAPI lists only GET/POST /api/v1/jobs (and the /astroapi/ai/jobs.json alias); there is no single-job endpoint — url is the Jobgether listing page.
- ~~`apply`~~ not offered: Page: Jobgether's own 'Auto Apply' is a paid premium feature for its users, not an API; listings link on to the employer.
- ~~`list_messages`~~ not offered: No messaging API; the OpenAPI documents the job search only.

## Credentials

None.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve jobgether   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve jobgether
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve jobgether   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/jobgether-mcp`. Python and TypeScript serve identical tools.
