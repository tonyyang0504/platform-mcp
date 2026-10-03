# OpenFIGI (instrument identifiers) MCP server

Category: **market_data** · Docs: https://www.openfigi.com/api/documentation · Verified: 2026-09-27

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/market_data/openfigi.json`; edit the catalog, not this file.

## Tools

- `search_symbols` — `POST /search` (https://www.openfigi.com/api/documentation)
- ~~`me`~~ not offered: No account endpoint; the optional API key is only a rate-limit tier.
- ~~`get_candles`~~ not offered: OpenFIGI serves identifiers only (mapping, search, filter), no prices.
- ~~`get_series`~~ not offered: No time series in the API (identifiers only).
- ~~`get_news`~~ not offered: No news endpoint in the API.

## Credentials

- `PLATFORM_MCP_OPENFIGI_API_KEY` — Optional OpenFIGI API key (sign up at https://www.openfigi.com/user/signup); raises the search limit from 5 to 20 requests per minute. Sent as X-OPENFIGI-APIKEY.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve openfigi   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve openfigi
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve openfigi   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/openfigi-mcp`. Python and TypeScript serve identical tools.
