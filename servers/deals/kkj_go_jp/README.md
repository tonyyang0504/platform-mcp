# Kankojyu Information Portal MCP server

Category: **deals** · Docs: https://www.kkj.go.jp/doc/ja/api_guide.pdf · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/deals/kkj_go_jp.json`; edit the catalog, not this file.

## Tools

- `search_postings` — `GET /api/` (https://www.kkj.go.jp/doc/ja/api_guide.pdf)
- ~~`me`~~ not offered: Keyless API ('ユーザー ID などのパラメーター…現時点では、用意していません'); no account.
- ~~`get_posting`~~ not offered: The API has search only (Query etc.); there is no lookup by Key.
- ~~`submit_bid`~~ not offered: Bids follow each agency's own procedure (the notice at url); the portal only aggregates notices.
- ~~`withdraw_bid`~~ not offered: No bid API (see submit_bid).
- ~~`bid_status`~~ not offered: No bid API (see submit_bid).
- ~~`list_messages`~~ not offered: No messaging API; only the public feed is machine-readable.
- ~~`send_message`~~ not offered: No messaging API; only the public feed is machine-readable.
- ~~`credits`~~ not offered: Keyless API; no account or credits.

## Credentials

None.

## Run

    uvx platform-mcp-hub serve kkj_go_jp          # Python
    npx -y platform-mcp-hub serve kkj_go_jp       # TypeScript
    claude mcp add kkj_go_jp -- uvx platform-mcp-hub serve kkj_go_jp

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/kkj_go_jp-mcp`. Python and TypeScript serve identical tools.
