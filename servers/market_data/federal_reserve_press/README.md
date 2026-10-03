# Federal Reserve Board - press releases (RSS) MCP server

Category: **market_data** · Docs: https://www.federalreserve.gov/feeds/feeds.htm · Verified: 2026-10-01

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/market_data/federal_reserve_press.json`; edit the catalog, not this file.

## Tools

- `get_news` — `GET /press_all.xml` (https://www.federalreserve.gov/feeds/press_all.xml)
- ~~`me`~~ not offered: Public feed: no accounts.
- ~~`get_candles`~~ not offered: No market data in this feed.
- ~~`get_series`~~ not offered: Economic series are published through FRED and the Data Download Program, not this feed.
- ~~`search_symbols`~~ not offered: No instruments in this feed.

## Credentials

None.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve federal_reserve_press   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve federal_reserve_press
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve federal_reserve_press   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/federal_reserve_press-mcp`. Python and TypeScript serve identical tools.
