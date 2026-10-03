# Landing.jobs MCP server

Category: **jobs** · Docs: https://github.com/landingjobs/LandingJobs-api/blob/master/README.md · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/jobs/landing_jobs.json`; edit the catalog, not this file.

## Tools

- `search` — `GET /jobs` (https://github.com/landingjobs/LandingJobs-api/blob/master/README.md#list-of-jobs)
- `get_posting` — `GET /jobs/{id}` (https://github.com/landingjobs/LandingJobs-api/blob/master/README.md#jobs-1)
- ~~`me`~~ not offered: The only account endpoint, GET /api/v1/user, needs a user API token ('Authorization: Token token=<API token>'), while 'Companies and Job endpoints do not require authentication'; this adapter is keyless, so there is no credential to verify.
- ~~`apply`~~ not offered: The API lists applications read-only ('Returns the list of applications made by the current user', GET /api/v1/user/applications); no endpoint creates an application - apply on the posting's url.
- ~~`list_messages`~~ not offered: No messaging endpoint; the documentation covers companies, jobs, the user, applications and referrals only.

## Credentials

None.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve landing_jobs   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve landing_jobs
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve landing_jobs   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/landing_jobs-mcp`. Python and TypeScript serve identical tools.
