# HackerOne MCP server

Category: **competitions** · Docs: https://api.hackerone.com/hacker-resources/ · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/competitions/hackerone.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /v1/hackers/payments/balance` (https://api.hackerone.com/hacker-resources/#balance-get-balance)
- `discover` — `GET /v1/hackers/programs` (https://api.hackerone.com/hacker-resources/#programs-get-programs)
- `get_competition` — `GET /v1/hackers/programs/{competition_id}` (https://api.hackerone.com/hacker-resources/#programs-get-program)
- `my_entries` — `GET /v1/hackers/me/reports` (https://api.hackerone.com/hacker-resources/#reports-get-reports)
- ~~`standings`~~ not offered: No leaderboard endpoint in the Hacker API (hacktivity is a disclosed-report feed, not a ranking).
- ~~`enter`~~ not offered: No join endpoint: public programs accept reports directly and private programs are invitation-only.
- ~~`submit`~~ not offered: POST /hackers/reports requires 'team_handle', 'title', 'vulnerability_information' and 'impact' (all required); the submit vocabulary has no title/impact fields, so it is not mapped.

## Credentials

- `PLATFORM_MCP_HACKERONE_API_USERNAME` — API token identifier from https://hackerone.com/settings/api_token/edit (used as the Basic auth username).
- `PLATFORM_MCP_HACKERONE_API_TOKEN` — API token value generated on the same page (used as the Basic auth password).

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve hackerone   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve hackerone
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve hackerone   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/hackerone-mcp`. Python and TypeScript serve identical tools.
