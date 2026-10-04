# 巨量引擎 Ocean Engine MCP server

Category: **ads** · Docs: https://open.oceanengine.com/labels/7/docs/1696710498372623 · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/ocean_engine.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /2/user/info/` (https://open.oceanengine.com/labels/7/docs/1696710507039756)
- `list_accounts` — `GET /oauth2/advertiser/get/` (https://open.oceanengine.com/labels/7/docs/1696710506574848)
- `list_campaigns` — `GET /v3.0/project/list/` (https://open.oceanengine.com/labels/7/docs/1740937147595776)
- `get_report` — `GET /v3.0/report/custom/get/` (https://open.oceanengine.com/labels/7/docs/1741387668314126)
- `update_budget` — `POST /v3.0/project/budget/update/` (https://open.oceanengine.com/labels/7/docs/1755353873798155)
- `pause_resume` — `POST /v3.0/project/status/update/` (https://open.oceanengine.com/labels/7/docs/1740941413906432)

## Credentials

- `PLATFORM_MCP_OCEAN_ENGINE_CLIENT_ID` — 开发者应用的 APP_ID (app_id) from 开发者后台 > 应用管理 (https://open.oceanengine.com/labels/7/docs/1696710506097679).
- `PLATFORM_MCP_OCEAN_ENGINE_CLIENT_SECRET` — 应用的私钥 Secret from 应用管理 > 编辑应用; sent as `secret` in the refresh call.
- `PLATFORM_MCP_OCEAN_ENGINE_REFRESH_TOKEN` — A refresh_token from 获取Access Token (auth_code exchange after the advertiser authorised the app). It is single-use: every refresh returns a new one and invalidates the old ('再次刷新需要使用本次刷新获取的新的RefreshToken'); set PLATFORM_MCP_STATE_DIR so the rotated token survives restarts.
- `PLATFORM_MCP_OCEAN_ENGINE_ADVERTISER_ID` — 投放账户 id (advertiser_id) used by update_budget and pause_resume, whose inputs carry only the project id; list_accounts shows the authorised ids.

## Run

    uvx platform-mcp-hub serve ocean_engine          # Python
    npx -y platform-mcp-hub serve ocean_engine       # TypeScript
    claude mcp add ocean_engine -- uvx platform-mcp-hub serve ocean_engine

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/ocean_engine-mcp`. Python and TypeScript serve identical tools.
