# Workable MCP server

Category: **jobs** · Docs: https://workable.readme.io/reference/job-board-api · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/jobs/workable.json`; edit the catalog, not this file.

## Tools

- `me` — `GET https://workable.com/spi/v3/accounts/{subdomain}` (https://workable.readme.io/reference/accountssubdomain)
- `search` — `GET /jobs` (https://workable.readme.io/reference/jobs)
- `get_posting` — `GET /jobs/{id}` (https://workable.readme.io/reference/jobsshortcode)
- ~~`apply`~~ not offered: POST /jobs/:shortcode/candidates 'Creates a candidate at the specified job' with the employer's w_candidates token, i.e. an ATS import by the company, not a job seeker applying; candidates apply at the job's application_url.
- ~~`list_messages`~~ not offered: The SPI v3 reference has no candidate messaging endpoints.

## Credentials

- `PLATFORM_MCP_WORKABLE_API_TOKEN` — Workable API access token (Settings > Integrations > Apps / API access token) with the r_jobs scope; sent as `Authorization: Bearer`. It is the employer account's token.
- `PLATFORM_MCP_WORKABLE_SUBDOMAIN` — The Workable account subdomain, e.g. 'groove-tech' in https://groove-tech.workable.com.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve workable   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve workable
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve workable   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/workable-mcp`. Python and TypeScript serve identical tools.
