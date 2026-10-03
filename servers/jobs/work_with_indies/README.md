# Work With Indies MCP server

Category: **jobs** · Docs: https://workwithindies.com/careers/rss.xml · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/jobs/work_with_indies.json`; edit the catalog, not this file.

## Tools

- `search` — `GET /careers/rss.xml` (https://www.workwithindies.com/careers/rss.xml)
- ~~`me`~~ not offered: No credentials to verify ('auth: none'): the feed is public and has no account endpoint.
- ~~`get_posting`~~ not offered: The feed has no per-item endpoint (each posting's url is an HTML page); search returns the whole record in raw.
- ~~`apply`~~ not offered: No application endpoint: the feed only lists postings; candidates apply on each posting's url (employer page / e-mail).
- ~~`list_messages`~~ not offered: No messaging API; the only machine-readable interface is the public job feed.

## Credentials

None.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve jobs/work_with_indies   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve jobs/work_with_indies
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve jobs/work_with_indies   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/work_with_indies-jobs-mcp`. Python and TypeScript serve identical tools.
