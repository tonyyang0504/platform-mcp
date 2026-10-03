# HigherGov MCP server

Category: **deals** · Docs: https://www.highergov.com/api-external/ · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/deals/highergov.json`; edit the catalog, not this file.

## Tools

- `search_postings` — `GET /opportunity/` (https://www.highergov.com/api-external/docs/#/api-external/api_external_opportunity_list)
- `get_posting` — `GET /opportunity/` (https://www.highergov.com/api-external/docs/#/api-external/api_external_opportunity_list)
- ~~`me`~~ not offered: No account endpoint in the OpenAPI schema; the api_key is a query parameter.
- ~~`submit_bid`~~ not offered: HigherGov is a market-intelligence database; offers go to the contracting agency named in the notice.
- ~~`withdraw_bid`~~ not offered: No bid API (see submit_bid).
- ~~`bid_status`~~ not offered: No bid API (see submit_bid).
- ~~`list_messages`~~ not offered: No messaging API is documented.
- ~~`send_message`~~ not offered: No messaging API is documented.
- ~~`credits`~~ not offered: Record usage is a monthly subscription allowance; no usage endpoint is documented.

## Credentials

- `PLATFORM_MCP_HIGHERGOV_API_KEY` — HigherGov API key (account admins: gear icon → API, per https://www.highergov.com/api-external/docs/).
- `PLATFORM_MCP_HIGHERGOV_SEARCH_ID` — Optional HigherGov SearchID of a saved opportunity search; the API has no keyword parameter, so filtering is done by a saved search.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve highergov   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve highergov
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve highergov   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/highergov-mcp`. Python and TypeScript serve identical tools.
