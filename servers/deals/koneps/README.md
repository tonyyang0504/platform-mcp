# KONEPS MCP server

Category: **deals** · Docs: https://www.data.go.kr/data/15129394/openapi.do · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/deals/koneps.json`; edit the catalog, not this file.

## Tools

- `search_postings` — `GET /getBidPblancListInfoServcPPSSrch` (https://www.data.go.kr/data/15129394/openapi.do)
- `get_posting` — `GET /getBidPblancListInfoServc` (https://www.data.go.kr/data/15129394/openapi.do)
- ~~`me`~~ not offered: The portal key has no account/introspection operation in this service.
- ~~`submit_bid`~~ not offered: Bids (투찰) are made in 나라장터 with a registered supplier certificate; the open API is read-only.
- ~~`withdraw_bid`~~ not offered: Read-only open API (see submit_bid).
- ~~`bid_status`~~ not offered: Read-only open API; bid results are a separate service (낙찰정보서비스) not mapped here.
- ~~`list_messages`~~ not offered: No messaging in the open API.
- ~~`send_message`~~ not offered: No messaging in the open API.
- ~~`credits`~~ not offered: The portal's daily call quota is shown only in the data.go.kr mypage; no API.

## Credentials

- `PLATFORM_MCP_KONEPS_SERVICE_KEY` — 공공데이터포털 (data.go.kr) 일반 인증키 (Decoding) for 조달청_나라장터 입찰공고정보서비스 (dataset 15129394), issued after an 활용신청.

## Run

    uvx platform-mcp-hub serve koneps          # Python
    npx -y platform-mcp-hub serve koneps       # TypeScript
    claude mcp add koneps -- uvx platform-mcp-hub serve koneps

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/koneps-mcp`. Python and TypeScript serve identical tools.
