# Codeforces MCP server

Category: **competitions** · Docs: https://codeforces.com/apiHelp · Verified: 2026-09-27

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/competitions/codeforces.json`; edit the catalog, not this file.

## Tools

- `discover` — `GET /contest.list` (https://codeforces.com/apiHelp/methods#contest.list)
- `get_competition` — `GET /contest.standings` (https://codeforces.com/apiHelp/methods#contest.standings)
- `standings` — `GET /contest.standings` (https://codeforces.com/apiHelp/methods#contest.standings)
- ~~`me`~~ not offered: Authorized methods need an API key and secret with a SHA-512 apiSig (https://codeforces.com/apiHelp); this entry serves the anonymous public methods only.
- ~~`my_entries`~~ not offered: user.status needs a handle, not an account session; no authenticated 'my entries' mapping in this public entry.
- ~~`enter`~~ not offered: Registration is done on the website; the API has no registration method.
- ~~`submit`~~ not offered: The API has no submission method (read-only API).

## Credentials

None.

## Run

    uvx platform-mcp-hub serve codeforces          # Python
    npx -y platform-mcp-hub serve codeforces       # TypeScript
    claude mcp add codeforces -- uvx platform-mcp-hub serve codeforces

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/codeforces-mcp`. Python and TypeScript serve identical tools.
