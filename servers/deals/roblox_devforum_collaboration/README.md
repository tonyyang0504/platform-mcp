# Roblox DevForum — Collaboration MCP server

Category: **deals** · Docs: https://devforum.roblox.com/c/collaboration/81.rss · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/deals/roblox_devforum_collaboration.json`; edit the catalog, not this file.

## Tools

- `search_postings` — `GET /search.json` (https://docs.discourse.org/#tag/Search/operation/search)
- `get_posting` — `GET /t/{id}.json` (https://docs.discourse.org/#tag/Topics/operation/getTopic)
- ~~`me`~~ not offered: Anonymous read-only access; a user API key would need the forum's user-api-key flow, which is not configured for third-party clients here.
- ~~`submit_bid`~~ not offered: Forum recruitment threads have no application object; candidates reply or message the poster on the forum with an account.
- ~~`withdraw_bid`~~ not offered: No application object (see submit_bid).
- ~~`bid_status`~~ not offered: No application object (see submit_bid).
- ~~`list_messages`~~ not offered: Private messages need a logged-in user API key; anonymous access cannot read them.
- ~~`send_message`~~ not offered: Posting or messaging needs a logged-in account on the forum; anonymous API access is read-only.
- ~~`credits`~~ not offered: No account, credit or balance concept on the forum.

## Credentials

None.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve roblox_devforum_collaboration   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve roblox_devforum_collaboration
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve roblox_devforum_collaboration   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/roblox_devforum_collaboration-mcp`. Python and TypeScript serve identical tools.
