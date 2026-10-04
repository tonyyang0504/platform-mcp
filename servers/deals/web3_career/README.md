# web3.career MCP server

Category: **deals** · Docs: https://web3.career/web3-jobs-api · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/deals/web3_career.json`; edit the catalog, not this file.

## Tools

- `search_postings` — `GET /v1` (https://docs.bondex.app/api-reference/openapi-documentation/web3.career-jobs-api)
- ~~`me`~~ not offered: No account endpoint; the token is only a query parameter of /v1.
- ~~`get_posting`~~ not offered: Single endpoint (/v1); no per-id lookup is documented — re-read the record from the search hit.
- ~~`submit_bid`~~ not offered: No application endpoint; apply_url sends the applicant to the posting.
- ~~`withdraw_bid`~~ not offered: No application endpoint (see submit_bid).
- ~~`bid_status`~~ not offered: No application endpoint (see submit_bid).
- ~~`list_messages`~~ not offered: No messaging API is documented.
- ~~`send_message`~~ not offered: No messaging API is documented.
- ~~`credits`~~ not offered: Free API; no credit or quota endpoint.

## Credentials

- `PLATFORM_MCP_WEB3_CAREER_TOKEN` — Web3.career API token generated at https://web3.career/web3-jobs-api after signing in ('Your token is for your use only … Do not share it'), sent as the token query parameter.

## Run

    uvx platform-mcp-hub serve deals/web3_career          # Python
    npx -y platform-mcp-hub serve deals/web3_career       # TypeScript
    claude mcp add web3_career -- uvx platform-mcp-hub serve deals/web3_career

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/web3_career-deals-mcp`. Python and TypeScript serve identical tools.
