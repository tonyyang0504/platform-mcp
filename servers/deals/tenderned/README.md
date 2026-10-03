# TenderNed MCP server

Category: **deals** · Docs: https://data.overheid.nl/dataset/aankondigingen-van-overheidsopdrachten---tenderned · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/deals/tenderned.json`; edit the catalog, not this file.

## Tools

- `search_postings` — `GET /publicaties` (https://data.overheid.nl/dataset/aankondigingen-van-overheidsopdrachten---tenderned)
- ~~`me`~~ not offered: The TNS webservice is keyless; there is no account endpoint.
- ~~`get_posting`~~ not offered: The only documented per-notice call is the XML API GET /publicaties/{publicatieId}/public-xml (https://www.tenderned.nl/info/swagger/), which 'is beveiligd via basic authentication' with credentials issued by functioneelbeheer@tenderned.nl and returns TED-schema XML; the keyless TNS documents only the list.
- ~~`submit_bid`~~ not offered: Tenders are submitted on the TenderNed platform with eHerkenning; neither the TNS nor the XML API accepts submissions (https://www.tenderned.nl/info/swagger/ has a single GET operation).
- ~~`withdraw_bid`~~ not offered: No bid API (see submit_bid).
- ~~`bid_status`~~ not offered: No bid API (see submit_bid).
- ~~`list_messages`~~ not offered: No messaging API is published (data.overheid.nl lists only the platform, RSS, TNS and XML API).
- ~~`send_message`~~ not offered: No messaging API is published.
- ~~`credits`~~ not offered: Free, keyless service; no quota endpoint.

## Credentials

None.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve tenderned   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve tenderned
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve tenderned   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/tenderned-mcp`. Python and TypeScript serve identical tools.
