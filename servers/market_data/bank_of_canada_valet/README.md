# Bank of Canada Valet MCP server

Category: **market_data** · Docs: https://www.bankofcanada.ca/valet/docs · Verified: 2026-10-01

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/market_data/bank_of_canada_valet.json`; edit the catalog, not this file.

## Tools

- `search_symbols` — `GET /lists/series/json` (https://www.bankofcanada.ca/valet/docs#/Lists/get_lists__type___format_)
- `get_series` — `GET /observations/{series_id}/json` (https://www.bankofcanada.ca/valet/docs#/Observations/get_observations__seriesNames___format_)
- ~~`me`~~ not offered: Open data: no accounts.
- ~~`get_candles`~~ not offered: No OHLC data (daily averages only).
- ~~`get_news`~~ not offered: Only an FX RSS feed (/fx_rss), not news; not mapped.

## Credentials

None.

## Run

    uvx platform-mcp-hub serve bank_of_canada_valet          # Python
    npx -y platform-mcp-hub serve bank_of_canada_valet       # TypeScript
    claude mcp add bank_of_canada_valet -- uvx platform-mcp-hub serve bank_of_canada_valet

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/bank_of_canada_valet-mcp`. Python and TypeScript serve identical tools.
