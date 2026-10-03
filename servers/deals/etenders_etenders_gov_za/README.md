# eTenders Portal MCP server

Category: **deals** · Docs: https://ocds-api.etenders.gov.za/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/deals/etenders_etenders_gov_za.json`; edit the catalog, not this file.

## Tools

- `search_postings` — `GET /api/OCDSReleases` (https://ocds-api.etenders.gov.za/swagger/v1/swagger.json)
- `get_posting` — `GET /api/OCDSReleases/release/{id}` (https://ocds-api.etenders.gov.za/swagger/v1/swagger.json)
- ~~`me`~~ not offered: Anonymous public API; no account.
- ~~`submit_bid`~~ not offered: Read-only OCDS publication API; bids are delivered to the procuring entity (hand delivery or its own channel per tender.specialConditions and the bid documents).
- ~~`withdraw_bid`~~ not offered: Read-only OCDS publication API (see submit_bid).
- ~~`bid_status`~~ not offered: Read-only OCDS publication API; award outcomes appear later as raw.awards on the release.
- ~~`list_messages`~~ not offered: No messaging; the API has only the two OCDSReleases GET operations.
- ~~`send_message`~~ not offered: No messaging; enquiries go to raw.tender.contactPerson.
- ~~`credits`~~ not offered: No account or credit endpoint.

## Credentials

None.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve etenders_etenders_gov_za   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve etenders_etenders_gov_za
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve etenders_etenders_gov_za   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/etenders_etenders_gov_za-mcp`. Python and TypeScript serve identical tools.
