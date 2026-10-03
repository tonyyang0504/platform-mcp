# Ashby MCP server

Category: **jobs** · Docs: https://developers.ashbyhq.com/reference/jobpostinglist · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/jobs/ashby.json`; edit the catalog, not this file.

## Tools

- `search` — `GET /posting-api/job-board/{job_board_name}` (https://developers.ashbyhq.com/docs/public-job-posting-api)
- ~~`me`~~ not offered: The posting API is public ('auth: none'); there is no account endpoint to verify.
- ~~`get_posting`~~ not offered: The public board has no per-posting endpoint; jobPosting.info is on the authenticated API, which 'requires the jobsRead permission' on the employer's API key. Re-read the record from the search hit.
- ~~`apply`~~ not offered: applicationForm.submit needs the employer's API key with candidatesWrite permission (https://developers.ashbyhq.com/reference/applicationformsubmit) and a multipart resume upload; candidates apply at the posting's applyUrl.
- ~~`list_messages`~~ not offered: No candidate messaging API.

## Credentials

- `PLATFORM_MCP_ASHBY_JOB_BOARD_NAME` — The organisation's Ashby jobs page name: the last path segment of its hosted board, e.g. 'Ashby' in https://jobs.ashbyhq.com/Ashby.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve ashby   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve ashby
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve ashby   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/ashby-mcp`. Python and TypeScript serve identical tools.
