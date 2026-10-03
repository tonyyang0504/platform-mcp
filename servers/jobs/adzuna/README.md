# Adzuna MCP server

Category: **jobs** · Docs: https://developer.adzuna.com/ · Verified: 2026-09-04

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/jobs/adzuna.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /jobs/gb/search/1` (https://developer.adzuna.com/docs/search)
- `search` — `GET /jobs/{country}/search/{page}` (https://developer.adzuna.com/docs/search)
- ~~`get_posting`~~ not offered: Page: 'no details endpoint — redirect_url opens the ad on the original board'; re-read the record from the search hit.
- ~~`apply`~~ not offered: Page: 'applying happens there' (on the original board); 'Aggregator — no account actions'.
- ~~`list_messages`~~ not offered: No messaging API: 'Aggregator — no account actions'.

## Credentials

- `PLATFORM_MCP_ADZUNA_APP_ID` — Adzuna app_id from https://developer.adzuna.com/ (register with username, e-mail, organisation name + website); mandatory app_id query parameter on every call.
- `PLATFORM_MCP_ADZUNA_APP_KEY` — Adzuna app_key from https://developer.adzuna.com/; mandatory app_key query parameter on every call.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve adzuna   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve adzuna
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve adzuna   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/adzuna-mcp`. Python and TypeScript serve identical tools.
