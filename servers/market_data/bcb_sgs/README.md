# Banco Central do Brasil - SGS (séries temporais) MCP server

Category: **market_data** · Docs: https://dadosabertos.bcb.gov.br/dataset/20542-saldo-da-carteira-de-credito-com-recursos-livres---total/resource/6e2b0c97-afab-4790-b8aa-b9542923cf88 · Verified: 2026-10-01

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/market_data/bcb_sgs.json`; edit the catalog, not this file.

## Tools

- `get_series` — `GET /bcdata.sgs.{series_id}/dados` (https://dadosabertos.bcb.gov.br/dataset/20542-saldo-da-carteira-de-credito-com-recursos-livres---total/resource/6e2b0c97-afab-4790-b8aa-b9542923cf88)
- ~~`me`~~ not offered: Open data: no accounts.
- ~~`get_candles`~~ not offered: No OHLC data.
- ~~`search_symbols`~~ not offered: SGS has no search API (the series catalogue is the web interface https://www3.bcb.gov.br/sgspub/).
- ~~`get_news`~~ not offered: No news endpoint.

## Credentials

None.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve bcb_sgs   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve bcb_sgs
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve bcb_sgs   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/bcb_sgs-mcp`. Python and TypeScript serve identical tools.
