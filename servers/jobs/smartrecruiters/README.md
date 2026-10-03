# SmartRecruiters MCP server

Category: **jobs** · Docs: https://developers.smartrecruiters.com/docs/posting-api · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/jobs/smartrecruiters.json`; edit the catalog, not this file.

## Tools

- `search` — `GET /companies/{company_identifier}/postings` (https://developers.smartrecruiters.com/docs/endpoints)
- `get_posting` — `GET /companies/{company_identifier}/postings/{id}` (https://developers.smartrecruiters.com/reference/v1getposting)
- ~~`me`~~ not offered: The public Posting API needs no credentials and has no account endpoint.
- ~~`apply`~~ not offered: The Application API (https://developers.smartrecruiters.com/docs/application-api) 'enables our customers and partners' to submit applications: 'All endpoints are protected' (customer API key or OAuth scope candidate_applications_manage) and the flow must present the posting's screening/diversity questions and privacy policies, which this vocabulary cannot carry; candidates apply at the posting's applyUrl.
- ~~`list_messages`~~ not offered: The Posting API has no messaging endpoints.

## Credentials

- `PLATFORM_MCP_SMARTRECRUITERS_COMPANY_IDENTIFIER` — The company identifier as it appears at the end of its SmartRecruiters career site, e.g. 'smartrecruiters' in https://careers.smartrecruiters.com/smartrecruiters.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve smartrecruiters   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve smartrecruiters
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve smartrecruiters   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/smartrecruiters-mcp`. Python and TypeScript serve identical tools.
