# Hacker News — Freelancer? Seeking freelancer? MCP server

Category: **deals** · Docs: https://github.com/HackerNews/API · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/deals/hacker_news_freelancer_seeking_freelancer.json`; edit the catalog, not this file.

## Tools

- `get_posting` — `GET /item/{id}.json` (https://github.com/HackerNews/API#items)
- ~~`search_postings`~~ not offered: Listing a month's posts takes two calls (GET /v0/user/whoishiring.json → submitted[] thread id, then GET /v0/item/<thread>.json → kids[]) plus one per comment; the API has no search endpoint and the adapter maps one call per verb.
- ~~`me`~~ not offered: No credentials and no account endpoint (read-only public API).
- ~~`submit_bid`~~ not offered: Replies are manual (HN has no write API).
- ~~`withdraw_bid`~~ not offered: No bid API (see submit_bid).
- ~~`bid_status`~~ not offered: No bid API (see submit_bid).
- ~~`list_messages`~~ not offered: HN has no private messaging.
- ~~`send_message`~~ not offered: HN has no write API.
- ~~`credits`~~ not offered: No account or credit endpoint.

## Credentials

None.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve hacker_news_freelancer_seeking_freelancer   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve hacker_news_freelancer_seeking_freelancer
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve hacker_news_freelancer_seeking_freelancer   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/hacker_news_freelancer_seeking_freelancer-mcp`. Python and TypeScript serve identical tools.
