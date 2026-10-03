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

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve codeforces   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve codeforces
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve codeforces   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/codeforces-mcp`. Python and TypeScript serve identical tools.
