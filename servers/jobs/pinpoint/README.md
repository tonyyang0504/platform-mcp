# Pinpoint MCP server

Category: **jobs** · Docs: https://developers.pinpointhq.com/docs/job-feeds-overview · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/jobs/pinpoint.json`; edit the catalog, not this file.

## Tools

- `search` — `GET /postings.json` (https://developers.pinpointhq.com/docs/jobs-json-endpoint)
- ~~`me`~~ not offered: The postings feed is public and keyless; there is no account endpoint to verify.
- ~~`get_posting`~~ not offered: The postings feed has no per-posting endpoint; re-read the record (id) from the search hit or open its url.
- ~~`apply`~~ not offered: Applications are made on the Pinpoint careers page (url); the authenticated API is the employer's (API key from the Pinpoint account), not a candidate apply endpoint.
- ~~`list_messages`~~ not offered: No candidate messaging in the public feed.

## Credentials

- `PLATFORM_MCP_PINPOINT_COMPANY_SUBDOMAIN` — The company's Pinpoint careers-site subdomain, e.g. 'workwithus' in https://workwithus.pinpointhq.com.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve pinpoint   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve pinpoint
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve pinpoint   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/pinpoint-mcp`. Python and TypeScript serve identical tools.
