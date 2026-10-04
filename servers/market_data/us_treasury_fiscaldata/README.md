# U.S. Treasury Fiscal Data MCP server

Category: **market_data** · Docs: https://fiscaldata.treasury.gov/api-documentation/ · Verified: 2026-10-01

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/market_data/us_treasury_fiscaldata.json`; edit the catalog, not this file.

## Tools

- `get_series` — `GET /v2/accounting/od/avg_interest_rates` (https://fiscaldata.treasury.gov/datasets/average-interest-rates-treasury-securities/average-interest-rates-on-u-s-treasury-securities)
- ~~`me`~~ not offered: Open data: no accounts.
- ~~`get_candles`~~ not offered: No OHLC data in Fiscal Data.
- ~~`search_symbols`~~ not offered: No series search endpoint; the security descriptions are listed in the dataset's data dictionary (see get_series note).
- ~~`get_news`~~ not offered: No news endpoint.

## Credentials

None.

## Run

    uvx platform-mcp-hub serve us_treasury_fiscaldata          # Python
    npx -y platform-mcp-hub serve us_treasury_fiscaldata       # TypeScript
    claude mcp add us_treasury_fiscaldata -- uvx platform-mcp-hub serve us_treasury_fiscaldata

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/us_treasury_fiscaldata-mcp`. Python and TypeScript serve identical tools.
