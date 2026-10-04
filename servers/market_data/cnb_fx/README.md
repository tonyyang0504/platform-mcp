# Česká národní banka - kurzy devizového trhu MCP server

Category: **market_data** · Docs: https://www.cnb.cz/cs/financni-trhy/devizovy-trh/kurzy-devizoveho-trhu/kurzy-devizoveho-trhu/ · Verified: 2026-10-01

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/market_data/cnb_fx.json`; edit the catalog, not this file.

## Tools

- `get_series` — `GET /rok.txt` (https://www.cnb.cz/cs/financni-trhy/devizovy-trh/kurzy-devizoveho-trhu/kurzy-devizoveho-trhu/rok.txt)
- ~~`me`~~ not offered: Open data: no accounts.
- ~~`get_candles`~~ not offered: Daily fixings only, no OHLC.
- ~~`search_symbols`~~ not offered: No series list endpoint; the column headers of rok.txt are the series (see get_series).
- ~~`get_news`~~ not offered: No news endpoint.

## Credentials

None.

## Run

    uvx platform-mcp-hub serve cnb_fx          # Python
    npx -y platform-mcp-hub serve cnb_fx       # TypeScript
    claude mcp add cnb_fx -- uvx platform-mcp-hub serve cnb_fx

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/cnb_fx-mcp`. Python and TypeScript serve identical tools.
