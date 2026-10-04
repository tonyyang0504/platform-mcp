# Platforma e-Zamówienia MCP server

Category: **deals** · Docs: https://ezamowienia.gov.pl/pl/informacje-dla-integratorow/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/deals/e_zamowienia.json`; edit the catalog, not this file.

## Tools

- `search_postings` — `GET /api/v1/notice` (https://media.ezamowienia.gov.pl/pod/2022/08/Zala%CC%A8cznik-3-Instrukcja-integracji-z-API-BZP.zip)
- `get_posting` — `GET /api/v1/notice` (https://media.ezamowienia.gov.pl/pod/2022/08/Zala%CC%A8cznik-3-Instrukcja-integracji-z-API-BZP.zip)
- ~~`me`~~ not offered: Reading BZP needs no account; the authenticated APIs (MT, MO, PP) are for integrated buyer systems after integration tests.
- ~~`submit_bid`~~ not offered: No offer API: offers are prepared and signed with a qualified e-signature inside the platform; the published APIs (BZP, MT, MO, PP, MMiA, CRD) cover notices, plans, reports and OCDS events.
- ~~`withdraw_bid`~~ not offered: No offer API (see submit_bid).
- ~~`bid_status`~~ not offered: No offer API (see submit_bid).
- ~~`list_messages`~~ not offered: Correspondence with the buyer happens inside the platform; no messaging API is published.
- ~~`send_message`~~ not offered: Correspondence with the buyer happens inside the platform; no messaging API is published.
- ~~`credits`~~ not offered: The platform is free; no account or credit endpoint.

## Credentials

None.

## Run

    uvx platform-mcp-hub serve e_zamowienia          # Python
    npx -y platform-mcp-hub serve e_zamowienia       # TypeScript
    claude mcp add e_zamowienia -- uvx platform-mcp-hub serve e_zamowienia

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/e_zamowienia-mcp`. Python and TypeScript serve identical tools.
