# Jolpica F1 (Ergast-compatible Formula 1 data) MCP server

Category: **competitions** · Docs: https://github.com/jolpica/jolpica-f1/blob/main/docs/README.md · Verified: 2026-10-01

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/competitions/jolpica_f1.json`; edit the catalog, not this file.

## Tools

- `discover` — `GET /current/races.json` (https://github.com/jolpica/jolpica-f1/blob/main/docs/endpoints/races.md)
- `get_competition` — `GET /{competition_id}/races.json` (https://github.com/jolpica/jolpica-f1/blob/main/docs/endpoints/races.md)
- `standings` — `GET /{competition_id}/results.json` (https://github.com/jolpica/jolpica-f1/blob/main/docs/endpoints/results.md)
- ~~`me`~~ not offered: No accounts.
- ~~`my_entries`~~ not offered: Not a participation platform.
- ~~`enter`~~ not offered: Not a participation platform.
- ~~`submit`~~ not offered: Not a participation platform.

## Credentials

None.

## Run

    uvx platform-mcp-hub serve jolpica_f1          # Python
    npx -y platform-mcp-hub serve jolpica_f1       # TypeScript
    claude mcp add jolpica_f1 -- uvx platform-mcp-hub serve jolpica_f1

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/jolpica_f1-mcp`. Python and TypeScript serve identical tools.
