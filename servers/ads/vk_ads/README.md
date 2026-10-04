# VK Ads (VK Реклама) MCP server

Category: **ads** · Docs: https://ads.vk.ru/doc/api/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/vk_ads.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /api/v3/user.json` (https://ads.vk.ru/ru/doc/api/resource/User)
- `list_campaigns` — `GET /api/v2/ad_plans.json` (https://ads.vk.ru/ru/doc/api/resource/AdPlans)
- `get_report` — `GET /api/v2/statistics/ad_plans/day.json` (https://ads.vk.ru/ru/doc/api/info/Statistics)
- `update_budget` — `POST /api/v2/ad_plans/{campaign_id}.json` (https://ads.vk.ru/ru/doc/api/resource/AdPlan)
- `pause_resume` — `POST /api/v2/ad_plans/{campaign_id}.json` (https://ads.vk.ru/ru/doc/api/resource/AdPlan)
- ~~`list_accounts`~~ not offered: Each VK Ads token is bound to one account ("доступ к данным аккаунта возможен только с токеном, полученным для данного аккаунта", https://ads.vk.ru/ru/doc/api/info/Авторизация в API); agency clients need their own agency_client_credentials token, so there is no multi-account listing for one token. Use me.

## Credentials

- `PLATFORM_MCP_VK_ADS_CLIENT_ID` — VK Ads API client_id (issued on request in the ad account settings; https://ads.vk.ru/ru/doc/api/info/Авторизация в API).
- `PLATFORM_MCP_VK_ADS_CLIENT_SECRET` — The API client's client_secret (form body of the token request).
- `PLATFORM_MCP_VK_ADS_REFRESH_TOKEN` — refresh_token from one POST /api/v2/oauth2/token.json with grant_type=client_credentials (your own account) or agency_client_credentials (an agency client). Refreshing does not create a new token instance, which keeps you under VK's per-user token limit; a token unused for a month is deleted and must be issued again.

## Run

    uvx platform-mcp-hub serve vk_ads          # Python
    npx -y platform-mcp-hub serve vk_ads       # TypeScript
    claude mcp add vk_ads -- uvx platform-mcp-hub serve vk_ads

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/vk_ads-mcp`. Python and TypeScript serve identical tools.
