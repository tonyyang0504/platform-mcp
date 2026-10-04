# service.bund.de — Ausschreibungen MCP server

Category: **deals** · Docs: https://www.service.bund.de/Content/DE/Ausschreibungen/Suche/Formular.html · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/deals/service_bund_de.json`; edit the catalog, not this file.

## Tools

- `search_postings` — `GET /Content/DE/Ausschreibungen/Suche/Formular.html` (https://www.service.bund.de/Content/DE/Ausschreibungen/Suche/Formular.html)
- ~~`me`~~ not offered: No credentials to verify ('auth: none'): the feed is public and has no account endpoint.
- ~~`get_posting`~~ not offered: Notice pages (/IMPORTE/Ausschreibungen/…html) are HTML only; there is no per-notice machine-readable endpoint.
- ~~`submit_bid`~~ not offered: Bids are submitted on the contracting authority's e-Vergabe platform linked from the notice; service.bund.de has no submission API.
- ~~`withdraw_bid`~~ not offered: No bid API (see submit_bid).
- ~~`bid_status`~~ not offered: No bid API (see submit_bid).
- ~~`list_messages`~~ not offered: No messaging API; only the public feed is machine-readable.
- ~~`send_message`~~ not offered: No messaging API; only the public feed is machine-readable.
- ~~`credits`~~ not offered: No account or credit endpoint; the feed is keyless.

## Credentials

None.

## Run

    uvx platform-mcp-hub serve service_bund_de          # Python
    npx -y platform-mcp-hub serve service_bund_de       # TypeScript
    claude mcp add service_bund_de -- uvx platform-mcp-hub serve service_bund_de

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/service_bund_de-mcp`. Python and TypeScript serve identical tools.
