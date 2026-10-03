# CoinPaprika MCP server

Category: **market_data** · Docs: https://docs.coinpaprika.com/api-reference/tools/search · Verified: 2026-10-01

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/market_data/coinpaprika.json`; edit the catalog, not this file.

## Tools

- `search_symbols` — `GET /search` (https://docs.coinpaprika.com/api-reference/tools/search)
- ~~`me`~~ not offered: The free API has no account endpoint.
- ~~`get_candles`~~ not offered: GET /coins/{coin_id}/ohlcv/historical answers 402 'Getting historical OHLCV data before <yesterday> is not allowed in this plan' on the free plan (live 2026-10-01); the latest-day endpoints return one candle, not a series.
- ~~`get_series`~~ not offered: No named macro/indicator series in this API.
- ~~`get_news`~~ not offered: Events per coin exist (/coins/{id}/events) but there is no headline search; not mapped.

## Credentials

None.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve coinpaprika   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve coinpaprika
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve coinpaprika   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/coinpaprika-mcp`. Python and TypeScript serve identical tools.
