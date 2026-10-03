# CJ Affiliate MCP server

Category: **ads** · Docs: https://developers.cj.com/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/cj_affiliate.json`; edit the catalog, not this file.

## Tools

- `me` — `POST /query` (https://developers.cj.com/graphql/reference/Commission%20Detail)
- `get_report` — `POST /query` (https://developers.cj.com/graphql/reference/Commission%20Detail)
- ~~`list_accounts`~~ not offered: The token is user-level and no GraphQL or REST API lists the advertiser companies a user can access (Commission Detail takes forAdvertisers CIDs; the Advertiser Lookup REST API is a publisher-side lookup of advertiser programs, https://developers.cj.com/docs/rest-apis/advertiser-lookup).
- ~~`list_campaigns`~~ not offered: CJ programs have no campaign objects in the API; the GraphQL APIs are Commission Detail, Item List, Product Feed, Program Terms, Promotional Properties and Tech Partner (https://developers.cj.com/graphql).
- ~~`update_budget`~~ not offered: No budget API: CJ is pay-per-action and the developer portal documents no budget endpoint (https://developers.cj.com/graphql).
- ~~`pause_resume`~~ not offered: No program or campaign status endpoint in the developer portal's GraphQL or REST APIs (https://developers.cj.com/graphql).

## Credentials

- `PLATFORM_MCP_CJ_AFFILIATE_PERSONAL_ACCESS_TOKEN` — CJ Developer Portal personal access token (https://developers.cj.com/account/personal-access-tokens), sent as `Authorization: Bearer`; it must belong to a user of the advertiser company (CID) queried.
- `PLATFORM_MCP_CJ_AFFILIATE_COMPANY_ID` — The advertiser's CJ company id (CID); used by the `me` probe (get_report takes it as account_id).

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve cj_affiliate   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve cj_affiliate
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve cj_affiliate   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/cj_affiliate-mcp`. Python and TypeScript serve identical tools.
