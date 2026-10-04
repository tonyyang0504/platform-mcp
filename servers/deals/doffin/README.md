# Doffin MCP server

Category: **deals** · Docs: https://www.doffin.no/info · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/deals/doffin.json`; edit the catalog, not this file.

## Tools

- `search_postings` — `GET /v2/search` (https://dof-notices-prod-api.developer.azure-api.net/api-details#api=651eeff38be0c56022ac741d&operation=65015b9b566f983bdcfcaee8)
- ~~`me`~~ not offered: The Public API has only search and download; there is no account or subscription endpoint.
- ~~`get_posting`~~ not offered: The only per-notice call, GET /v2/download/{doffinId} ('Download notice'), returns the notice document itself; the portal publishes no response schema for it (only for search), so it cannot be mapped to fields. Use search_postings with the Doffin id in `query`, or open https://www.doffin.no/notices/<id>.
- ~~`submit_bid`~~ not offered: Doffin is a notice board; tenders are delivered on the buyer's tendering system, and the Notices API (eform-api) only publishes notices for buyers.
- ~~`withdraw_bid`~~ not offered: No bid API (see submit_bid).
- ~~`bid_status`~~ not offered: No bid API (see submit_bid).
- ~~`list_messages`~~ not offered: No messaging in the Public API (search and download only).
- ~~`send_message`~~ not offered: No messaging in the Public API (search and download only).
- ~~`credits`~~ not offered: No credit or quota endpoint.

## Credentials

- `PLATFORM_MCP_DOFFIN_SUBSCRIPTION_KEY` — Subscription key for the 'Public API' product from the Doffin API developer portal (https://dof-notices-prod-api.developer.azure-api.net/, sign up → Products → subscribe), sent as the Ocp-Apim-Subscription-Key header.

## Run

    uvx platform-mcp-hub serve doffin          # Python
    npx -y platform-mcp-hub serve doffin       # TypeScript
    claude mcp add doffin -- uvx platform-mcp-hub serve doffin

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/doffin-mcp`. Python and TypeScript serve identical tools.
