# World Bank Procurement Notices MCP server

Category: **deals** · Docs: https://search.worldbank.org/api/v2/procnotices?format=json · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/deals/world_bank_procurement.json`; edit the catalog, not this file.

## Tools

- `search_postings` — `GET /procnotices` (https://documents.worldbank.org/en/publication/documents-reports/api)
- `get_posting` — `GET /procnotices` (https://documents.worldbank.org/en/publication/documents-reports/api)
- ~~`me`~~ not offered: No credentials to verify ('auth: none') and no account endpoint.
- ~~`submit_bid`~~ not offered: Bids are submitted to the borrower's implementing agency as each notice instructs; the API is read-only.
- ~~`withdraw_bid`~~ not offered: No bid API (see submit_bid).
- ~~`bid_status`~~ not offered: No bid API (see submit_bid).
- ~~`list_messages`~~ not offered: No messaging API is documented.
- ~~`send_message`~~ not offered: No messaging API is documented.
- ~~`credits`~~ not offered: No account or credit endpoint; the API is keyless.

## Credentials

None.

## Run

    uvx platform-mcp-hub serve world_bank_procurement          # Python
    npx -y platform-mcp-hub serve world_bank_procurement       # TypeScript
    claude mcp add world_bank_procurement -- uvx platform-mcp-hub serve world_bank_procurement

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/world_bank_procurement-mcp`. Python and TypeScript serve identical tools.
