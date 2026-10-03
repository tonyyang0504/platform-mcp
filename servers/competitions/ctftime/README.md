# CTFtime (capture-the-flag events) MCP server

Category: **competitions** · Docs: https://ctftime.org/api/ · Verified: 2026-10-01

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/competitions/ctftime.json`; edit the catalog, not this file.

## Tools

- `discover` — `GET /events/` (https://ctftime.org/api/)
- `get_competition` — `GET /events/{competition_id}/` (https://ctftime.org/api/)
- `standings` — `GET /results/` (https://ctftime.org/api/)
- ~~`me`~~ not offered: No accounts in the public API.
- ~~`my_entries`~~ not offered: Team participation needs a login; not in the public API.
- ~~`enter`~~ not offered: Registration happens on each event's own site; not an API call.
- ~~`submit`~~ not offered: Flags are submitted on each event's own platform.

## Credentials

None.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve ctftime   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve ctftime
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve ctftime   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/ctftime-mcp`. Python and TypeScript serve identical tools.
