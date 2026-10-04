# OpenLigaDB (Fußball-Bundesliga und weitere Ligen) MCP server

Category: **competitions** · Docs: https://api.openligadb.de/index.html · Verified: 2026-10-01

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/competitions/openligadb.json`; edit the catalog, not this file.

## Tools

- `discover` — `GET /getavailableleagues` (https://api.openligadb.de/index.html#/Liga/get_getavailableleagues)
- `standings` — `GET /getbltable/{competition_id}` (https://api.openligadb.de/index.html#/Tabelle/get_getbltable__leagueShortcut___leagueSeason_)
- ~~`me`~~ not offered: No accounts.
- ~~`get_competition`~~ not offered: There is no endpoint for one league-season's details (only the full list in discover and match data per matchday).
- ~~`my_entries`~~ not offered: Not a participation platform.
- ~~`enter`~~ not offered: Not a participation platform.
- ~~`submit`~~ not offered: Not a participation platform.

## Credentials

None.

## Run

    uvx platform-mcp-hub serve openligadb          # Python
    npx -y platform-mcp-hub serve openligadb       # TypeScript
    claude mcp add openligadb -- uvx platform-mcp-hub serve openligadb

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/openligadb-mcp`. Python and TypeScript serve identical tools.
