# Банк России - DailyInfo (веб-сервис) MCP server

Category: **market_data** · Docs: https://www.cbr.ru/development/DWS/ · Verified: 2026-10-01

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/market_data/cbr_dailyinfo.json`; edit the catalog, not this file.

## Tools

- `search_symbols` — `POST ` (https://www.cbr.ru/development/DWS/)
- `get_series` — `POST ` (https://www.cbr.ru/development/DWS/)
- ~~`me`~~ not offered: Public web service: no accounts.
- ~~`get_candles`~~ not offered: Official daily rates only, no OHLC.
- ~~`get_news`~~ not offered: The service has no news operation (MainInfoXML returns key rates, not headlines).

## Credentials

None.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve cbr_dailyinfo   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve cbr_dailyinfo
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve cbr_dailyinfo   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/cbr_dailyinfo-mcp`. Python and TypeScript serve identical tools.
