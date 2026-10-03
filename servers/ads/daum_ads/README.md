# Daum search ads (now Kakao 키워드광고) MCP server

Category: **ads** · Docs: https://developers.kakao.com/docs/latest/ko/keyword-ad/common · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/daum_ads.json`; edit the catalog, not this file.

## Tools

- `me` — `GET https://kapi.kakao.com/v1/business/tokeninfo` (https://developers.kakao.com/docs/latest/ko/business-auth/rest-api)
- `list_accounts` — `GET /openapi/v1/adAccounts/pages` (https://developers.kakao.com/docs/latest/ko/keyword-ad/ad-account)
- `list_campaigns` — `GET /openapi/v1/campaigns` (https://developers.kakao.com/docs/latest/ko/keyword-ad/campaign)
- `get_report` — `GET /openapi/v1/campaigns/report` (https://developers.kakao.com/docs/latest/ko/keyword-ad/report)
- `update_budget` — `PATCH /openapi/v1/campaigns/{campaign_id}/dailyBudget` (https://developers.kakao.com/docs/latest/ko/keyword-ad/campaign)
- `pause_resume` — `PATCH /openapi/v1/campaigns/{campaign_id}/onOff` (https://developers.kakao.com/docs/latest/ko/keyword-ad/campaign)

## Credentials

- `PLATFORM_MCP_DAUM_ADS_BUSINESS_TOKEN` — Kakao business token (비즈니스 토큰) issued by POST https://kauth.kakao.com/oauth/business/token after the advertiser consents to the keyword_management scope in your biz app (https://developers.kakao.com/docs/latest/ko/business-auth/rest-api). It has no refresh flow; it expires after long non-use.
- `PLATFORM_MCP_DAUM_ADS_AD_ACCOUNT_ID` — Kakao keyword ad account id (numeric, without the K prefix), sent as the `adAccountId` header that every campaign and report call requires.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve daum_ads   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve daum_ads
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve daum_ads   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/daum_ads-mcp`. Python and TypeScript serve identical tools.
