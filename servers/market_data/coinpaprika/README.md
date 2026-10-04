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

    uvx platform-mcp-hub serve coinpaprika          # Python
    npx -y platform-mcp-hub serve coinpaprika       # TypeScript
    claude mcp add coinpaprika -- uvx platform-mcp-hub serve coinpaprika

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/coinpaprika-mcp`. Python and TypeScript serve identical tools.
