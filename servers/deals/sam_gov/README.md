# SAM MCP server

Category: **deals** · Docs: https://open.gsa.gov/api/get-opportunities-public-api/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/deals/sam_gov.json`; edit the catalog, not this file.

## Tools

- `search_postings` — `GET /opportunities/v2/search` (https://open.gsa.gov/api/get-opportunities-public-api/)
- `get_posting` — `GET /opportunities/v2/search` (https://open.gsa.gov/api/get-opportunities-public-api/)
- ~~`me`~~ not offered: No key-introspection endpoint in the Opportunities API.
- ~~`submit_bid`~~ not offered: No offer submission API; each notice says where to send offers (contracting office).
- ~~`withdraw_bid`~~ not offered: No offer API (see submit_bid).
- ~~`bid_status`~~ not offered: No offer API (see submit_bid).
- ~~`list_messages`~~ not offered: No messaging API.
- ~~`send_message`~~ not offered: No messaging API.
- ~~`credits`~~ not offered: Daily limits depend on the account role; no quota endpoint.

## Credentials

- `PLATFORM_MCP_SAM_GOV_API_KEY` — SAM.gov public API key: sign in to SAM.gov → Account Details → generate the public API key (daily request limits depend on the account's role).

## Run

    uvx platform-mcp-hub serve sam_gov          # Python
    npx -y platform-mcp-hub serve sam_gov       # TypeScript
    claude mcp add sam_gov -- uvx platform-mcp-hub serve sam_gov

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/sam_gov-mcp`. Python and TypeScript serve identical tools.
