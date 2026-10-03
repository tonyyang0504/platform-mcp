# Narodowy Bank Polski - kursy walut MCP server

Category: **market_data** · Docs: https://api.nbp.pl/ · Verified: 2026-10-01

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/market_data/nbp_rates.json`; edit the catalog, not this file.

## Tools

- `search_symbols` — `GET /exchangerates/tables/A/` (https://api.nbp.pl/#kursyWalut)
- `get_series` — `GET /exchangerates/rates/{series_id}/{window}/` (https://api.nbp.pl/#kursyWalut)
- ~~`me`~~ not offered: Open API: no accounts.
- ~~`get_candles`~~ not offered: No OHLC data (gold prices and fixings only).
- ~~`get_news`~~ not offered: No news endpoint.

## Credentials

None.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve nbp_rates   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve nbp_rates
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve nbp_rates   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/nbp_rates-mcp`. Python and TypeScript serve identical tools.
