# TalentLyft MCP server

Category: **jobs** · Docs: https://developers.talentlyft.com/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/jobs/talentlyft.json`; edit the catalog, not this file.

## Tools

- `search` — `GET /{subdomain}/jobs` (https://developers.talentlyft.com/public-api-reference/jobs)
- ~~`me`~~ not offered: The Public Customer API needs no token and has no account endpoint.
- ~~`get_posting`~~ not offered: The public API reference documents only the jobs, departments and locations lists; there is no public single-job endpoint. Re-read the record from the search hit.
- ~~`apply`~~ not offered: Creating candidates/applications is in the Private Customer API with the company's API token ('manipulation of candidates … candidate applications'), not a candidate credential; candidates apply through the job's ShortlinkUrl.
- ~~`list_messages`~~ not offered: No candidate messaging in the public API.

## Credentials

- `PLATFORM_MCP_TALENTLYFT_SUBDOMAIN` — The company's TalentLyft careers-site subdomain, e.g. 'demo' in https://demo.talentlyft.com.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve talentlyft   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve talentlyft
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve talentlyft   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/talentlyft-mcp`. Python and TypeScript serve identical tools.
