# arXiv Quantitative Finance (q-fin) papers MCP server

Category: **market_data** · Docs: https://info.arxiv.org/help/api/user-manual.html · Verified: 2026-10-01

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/market_data/arxiv_qfin.json`; edit the catalog, not this file.

## Tools

- `get_news` — `GET /query` (https://info.arxiv.org/help/api/user-manual.html#_query_interface)
- ~~`me`~~ not offered: No accounts in the API.
- ~~`get_candles`~~ not offered: Papers, not market data.
- ~~`get_series`~~ not offered: Papers, not series.
- ~~`search_symbols`~~ not offered: Papers, not instruments.

## Credentials

None.

## Run

    uvx platform-mcp-hub serve arxiv_qfin          # Python
    npx -y platform-mcp-hub serve arxiv_qfin       # TypeScript
    claude mcp add arxiv_qfin -- uvx platform-mcp-hub serve arxiv_qfin

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/arxiv_qfin-mcp`. Python and TypeScript serve identical tools.
