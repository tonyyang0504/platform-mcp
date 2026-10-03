# TikTok One (Creator Marketplace) MCP server

Category: **ads** · Docs: https://business-api.tiktok.com/portal/docs/get-tto-creator-marketplace-campaigns/v1.3 · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/tiktok_creator_marketplace.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /tto/oauth2/tcm/` (https://business-api.tiktok.com/portal/docs?id=1815693478150146)
- `list_campaigns` — `GET /tto/tcm/campaign/` (https://business-api.tiktok.com/portal/docs/get-tto-creator-marketplace-campaigns/v1.3)
- ~~`list_accounts`~~ not offered: The account listing "GET /tto/oauth2/tcm/" returns a bare array of id strings (data.tto_tcm_account_ids, https://business-api.tiktok.com/portal/docs?id=1815693478150146), which the adapter cannot map to account records; me returns it.
- ~~`get_report`~~ not offered: TTO Creator Marketplace reports are video-level per campaign and region ("/tto/tcm/report/" with a Country-Code header, https://business-api.tiktok.com/portal/docs?id=1815693573340162), not campaign spend over a date range.
- ~~`update_budget`~~ not offered: TTO Creator Marketplace campaigns have no budget field (https://business-api.tiktok.com/portal/docs/get-tto-creator-marketplace-campaigns/v1.3); paid delivery is managed through the TikTok Ads API (the `tiktok` entry).
- ~~`pause_resume`~~ not offered: TTO Creator Marketplace campaigns have no pause/resume status (https://business-api.tiktok.com/portal/docs/get-tto-creator-marketplace-campaigns/v1.3).

## Credentials

- `PLATFORM_MCP_TIKTOK_CREATOR_MARKETPLACE_ACCESS_TOKEN` — Access token authorized by a TikTok One Creator Marketplace account (auth_code exchanged at /oauth2/access_token/); it does not expire unless the account revokes it (https://business-api.tiktok.com/portal/docs/obtain-authorization-and-authentication-from-a-tto-creator-marketplace-account/v1.3).
- `PLATFORM_MCP_TIKTOK_CREATOR_MARKETPLACE_APP_SECRET` — Secret of your TikTok for Business developer app, needed by the account-listing call used by me.
- `PLATFORM_MCP_TIKTOK_CREATOR_MARKETPLACE_APP_ID` — App ID of your TikTok for Business developer app (My Apps > App Detail > Basic Information).

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve tiktok_creator_marketplace   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve tiktok_creator_marketplace
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve tiktok_creator_marketplace   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/tiktok_creator_marketplace-mcp`. Python and TypeScript serve identical tools.
