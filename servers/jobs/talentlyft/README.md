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

    uvx platform-mcp-hub serve talentlyft          # Python
    npx -y platform-mcp-hub serve talentlyft       # TypeScript
    claude mcp add talentlyft -- uvx platform-mcp-hub serve talentlyft

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/talentlyft-mcp`. Python and TypeScript serve identical tools.
