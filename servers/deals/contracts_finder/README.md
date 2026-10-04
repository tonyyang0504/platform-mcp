# Contracts Finder MCP server

Category: **deals** · Docs: https://www.contractsfinder.service.gov.uk/apidocumentation/ · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/deals/contracts_finder.json`; edit the catalog, not this file.

## Tools

- `search_postings` — `GET /Published/Notices/OCDS/Search` (https://www.contractsfinder.service.gov.uk/apidocumentation/Notices/1/GET-Published-Notice-OCDS-Search)
- `get_posting` — `GET /Published/OCDS/Release/{id}` (https://www.contractsfinder.service.gov.uk/apidocumentation/Notices/1/GET-Published-OCDS-Release)
- ~~`submit_bid`~~ not offered: Page: 'No proposal / message / contract endpoint exists — responses are lodged on the buyer's e-tendering system'; the only writes (draft/publish notices) are for approved eOpportunity providers.
- ~~`withdraw_bid`~~ not offered: No bid API (see submit_bid).
- ~~`bid_status`~~ not offered: No bid API (see submit_bid).
- ~~`list_messages`~~ not offered: No messaging API; the page documents the public listing feed only.
- ~~`send_message`~~ not offered: No messaging API; the page documents the public listing feed only.
- ~~`credits`~~ not offered: No account or credit endpoint; the feed is keyless.
- ~~`me`~~ not offered: No credentials to verify ('auth: none') and no account endpoint.

## Credentials

None.

## Run

    uvx platform-mcp-hub serve contracts_finder          # Python
    npx -y platform-mcp-hub serve contracts_finder       # TypeScript
    claude mcp add contracts_finder -- uvx platform-mcp-hub serve contracts_finder

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/contracts_finder-mcp`. Python and TypeScript serve identical tools.
