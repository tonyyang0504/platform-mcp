# Breezy HR MCP server

Category: **jobs** · Docs: https://developer.breezy.hr/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/jobs/breezy_hr.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /user` (https://developer.breezy.hr/reference/getuser)
- `search` — `GET /company/{company_id}/positions` (https://developer.breezy.hr/reference/listpositions)
- `get_posting` — `GET /company/{company_id}/position/{id}` (https://developer.breezy.hr/reference/getposition)
- ~~`apply`~~ not offered: The API is for the employer's own account: POST /company/{id}/position/{id}/candidates 'Creates a candidate on the specified position' as the recruiter (origin sourced/applied), which is not a job seeker applying; candidates apply on the company's Breezy careers page.
- ~~`list_messages`~~ not offered: Candidate conversations are per candidate (GET /company/{id}/position/{id}/candidate/{id}/conversation needs both a position and a candidate id), so there is no single inbox call that fits list_messages(thread_id).

## Credentials

- `PLATFORM_MCP_BREEZY_HR_API_TOKEN` — Breezy Personal Access Token (prefix breezy_pat_) from the Breezy app: user icon > My Settings > API Keys > Create API Key; sent as `Authorization: Bearer`. It acts as the Breezy user who created it.
- `PLATFORM_MCP_BREEZY_HR_COMPANY_ID` — The Breezy company id (12-14 character hex `_id` from GET /v3/companies) whose positions are read.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve breezy_hr   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve breezy_hr
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve breezy_hr   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/breezy_hr-mcp`. Python and TypeScript serve identical tools.
