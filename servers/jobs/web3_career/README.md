# Web3 Career MCP server

Category: **jobs** · Docs: https://docs.bondex.app/api-reference · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/jobs/web3_career.json`; edit the catalog, not this file.

## Tools

- `search` — `GET /v1` (https://docs.bondex.app/api-reference/openapi-documentation/web3.career-jobs-api)
- ~~`me`~~ not offered: No account endpoint; the token is a query parameter only.
- ~~`get_posting`~~ not offered: Single endpoint (/v1); no per-id lookup is documented.
- ~~`apply`~~ not offered: No application endpoint; apply_url sends the applicant to the posting.
- ~~`list_messages`~~ not offered: No messaging API is documented.

## Credentials

- `PLATFORM_MCP_WEB3_CAREER_TOKEN` — Web3.career API token from https://web3.career/web3-jobs-api ('Your token is for your use only … Do not share it').

## Run

    uvx platform-mcp-hub serve jobs/web3_career          # Python
    npx -y platform-mcp-hub serve jobs/web3_career       # TypeScript
    claude mcp add web3_career -- uvx platform-mcp-hub serve jobs/web3_career

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/web3_career-jobs-mcp`. Python and TypeScript serve identical tools.
