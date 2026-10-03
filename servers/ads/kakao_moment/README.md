# 카카오모먼트 Kakao Moment MCP server

Category: **ads** · Docs: https://developers.kakao.com/docs/latest/ko/kakaomoment/common · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/kakao_moment.json`; edit the catalog, not this file.

## Tools

- `me` — `GET https://kapi.kakao.com/v1/business/tokeninfo` (https://developers.kakao.com/docs/latest/ko/business-auth/rest-api)
- `list_accounts` — `GET /openapi/v4/adAccounts/pages` (https://developers.kakao.com/docs/latest/ko/kakaomoment/ad-account)
- `list_campaigns` — `GET /openapi/v4/campaigns` (https://developers.kakao.com/docs/latest/ko/kakaomoment/campaign)
- `get_report` — `GET /openapi/v4/campaigns/report` (https://developers.kakao.com/docs/latest/ko/kakaomoment/report)
- `update_budget` — `PUT /openapi/v4/campaigns/dailyBudgetAmount` (https://developers.kakao.com/docs/latest/ko/kakaomoment/campaign)
- `pause_resume` — `PUT /openapi/v4/campaigns/onOff` (https://developers.kakao.com/docs/latest/ko/kakaomoment/campaign)

## Credentials

- `PLATFORM_MCP_KAKAO_MOMENT_BUSINESS_TOKEN` — Kakao business token (비즈니스 토큰) issued by POST https://kauth.kakao.com/oauth/business/token after the advertiser consents to moment_management in your biz app (https://developers.kakao.com/docs/latest/ko/business-auth/rest-api). No refresh flow; it expires after long non-use.
- `PLATFORM_MCP_KAKAO_MOMENT_AD_ACCOUNT_ID` — Kakao Moment ad account number, sent as the `adAccountId` header that campaign and report calls require.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve kakao_moment   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve kakao_moment
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve kakao_moment   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/kakao_moment-mcp`. Python and TypeScript serve identical tools.
