# Swiss National Bank data portal MCP server

Category: **market_data** · Docs: https://data.snb.ch/en/help · Verified: 2026-10-01

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/market_data/snb_data.json`; edit the catalog, not this file.

## Tools

- `get_series` — `GET /cube/{cube}/data/csv/en` (https://data.snb.ch/en/help)
- ~~`me`~~ not offered: Open data: no accounts.
- ~~`get_candles`~~ not offered: No OHLC data.
- ~~`search_symbols`~~ not offered: There is no cube search API; cube ids are listed on the portal's topic pages and dimensions at /api/cube/{cube}/dimensions/en.
- ~~`get_news`~~ not offered: No news endpoint.

## Credentials

None.

## Run

    uvx platform-mcp-hub serve snb_data          # Python
    npx -y platform-mcp-hub serve snb_data       # TypeScript
    claude mcp add snb_data -- uvx platform-mcp-hub serve snb_data

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/snb_data-mcp`. Python and TypeScript serve identical tools.
