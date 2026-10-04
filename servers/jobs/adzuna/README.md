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

    uvx platform-mcp-hub serve adzuna          # Python
    npx -y platform-mcp-hub serve adzuna       # TypeScript
    claude mcp add adzuna -- uvx platform-mcp-hub serve adzuna

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/adzuna-mcp`. Python and TypeScript serve identical tools.
