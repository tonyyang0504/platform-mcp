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

    uvx platform-mcp-hub serve cbr_dailyinfo          # Python
    npx -y platform-mcp-hub serve cbr_dailyinfo       # TypeScript
    claude mcp add cbr_dailyinfo -- uvx platform-mcp-hub serve cbr_dailyinfo

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/cbr_dailyinfo-mcp`. Python and TypeScript serve identical tools.
