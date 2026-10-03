# NHS Jobs MCP server

Category: **jobs** · Docs: https://www.nhsbsa.nhs.uk/about-nhs-jobs/nhs-jobs-integration-and-benefits · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/jobs/nhs_jobs.json`; edit the catalog, not this file.

## Tools

- `search` — `GET /search_xml` (https://www.nhsbsa.nhs.uk/sites/default/files/2026-05/NHS%20Jobs%20Self-Serve%20Job%20Adverts%20API%20V1.07_0.docx)
- `get_posting` — `GET /search_xml` (https://www.nhsbsa.nhs.uk/sites/default/files/2026-05/NHS%20Jobs%20Self-Serve%20Job%20Adverts%20API%20V1.07_0.docx)
- ~~`me`~~ not offered: No credentials to verify: the Self-Serve API is keyless and has no account endpoint.
- ~~`apply`~~ not offered: No application endpoint: the spec only retrieves adverts ('receive back live job adverts'); candidates apply on the advert's url.
- ~~`list_messages`~~ not offered: No messaging endpoint; the spec covers the search XML and RSS feeds and search links only.

## Credentials

None.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve nhs_jobs   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve nhs_jobs
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve nhs_jobs   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/nhs_jobs-mcp`. Python and TypeScript serve identical tools.
