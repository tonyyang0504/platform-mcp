# EU Remote Jobs MCP server

Category: **jobs** · Docs: https://euremotejobs.com/wp-json/wp/v2/job-listings · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/jobs/euremotejobs.json`; edit the catalog, not this file.

## Tools

- `search` — `GET /job-listings` (https://developer.wordpress.org/rest-api/reference/posts/#list-posts)
- `get_posting` — `GET /job-listings/{id}` (https://developer.wordpress.org/rest-api/reference/posts/#retrieve-a-post)
- ~~`me`~~ not offered: No credentials to verify: the WordPress REST API is read publicly and the site offers no job-seeker account API.
- ~~`apply`~~ not offered: Applications go to each listing's meta._application (an employer URL or e-mail); the site has no application endpoint.
- ~~`list_messages`~~ not offered: No messaging endpoint in the site's REST index; only job listings are exposed.

## Credentials

None.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve euremotejobs   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve euremotejobs
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve euremotejobs   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/euremotejobs-mcp`. Python and TypeScript serve identical tools.
