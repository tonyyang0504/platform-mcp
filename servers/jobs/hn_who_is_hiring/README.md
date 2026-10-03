# Hacker News: Who is hiring? MCP server

Category: **jobs** · Docs: https://github.com/HackerNews/API · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/jobs/hn_who_is_hiring.json`; edit the catalog, not this file.

## Tools

- `get_posting` — `GET /item/{id}.json` (https://github.com/HackerNews/API#items)
- ~~`search`~~ not offered: Listing a month's postings takes two calls (GET /v0/user/whoishiring.json → submitted[] thread id, then GET /v0/item/<thread>.json → kids[] comment ids) plus one call per comment; the API has no search endpoint and the adapter maps one call per verb.
- ~~`me`~~ not offered: No credentials and no account endpoint (read-only public API).
- ~~`apply`~~ not offered: Applications are e-mails or links named in each comment; HN has no write API.
- ~~`list_messages`~~ not offered: HN has no private messaging.

## Credentials

None.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve hn_who_is_hiring   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve hn_who_is_hiring
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve hn_who_is_hiring   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/hn_who_is_hiring-mcp`. Python and TypeScript serve identical tools.
