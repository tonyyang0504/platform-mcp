# 磁力引擎 Kuaishou Magnetic Engine MCP server

Category: **ads** · Docs: https://developers.e.kuaishou.com/docs?docType=DSP&documentId=2539&menuId=3765 · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/kuaishou_magnetic_engine.json`; edit the catalog, not this file.

## Tools

- `me` — `POST /gw/dsp/campaign/list` (https://developers.e.kuaishou.com/docs?docType=DSP&documentId=2261&menuId=2806)
- `list_campaigns` — `POST /gw/dsp/campaign/list` (https://developers.e.kuaishou.com/docs?docType=DSP&documentId=2261&menuId=2806)
- `get_report` — `POST /v1/report/campaign_report` (https://developers.e.kuaishou.com/docs?docType=DSP&documentId=2025&menuId=2407)
- `update_budget` — `POST /gw/dsp/campaign/update` (https://developers.e.kuaishou.com/docs?docType=DSP&documentId=2260&menuId=2805)
- `pause_resume` — `POST /v1/campaign/update/status` (https://developers.e.kuaishou.com/docs?docType=DSP&documentId=1930&menuId=2382)
- ~~`list_accounts`~~ not offered: 拉取token下授权广告账户接口 (POST /rest/openapi/oauth2/authorize/approval/list, https://developers.e.kuaishou.com/docs?docType=DSP&documentId=1995&menuId=3797) takes 'app_id', 'secret' and 'access_token | 查询的 access_token' inside the JSON body; the runtime cannot put the token it minted into a request body, so the advertiser is configured as advertiser_id instead.

## Credentials

- `PLATFORM_MCP_KUAISHOU_MAGNETIC_ENGINE_CLIENT_ID` — app_id returned when the 磁力引擎 MAPI developer application was approved (开发者平台 > 应用).
- `PLATFORM_MCP_KUAISHOU_MAGNETIC_ENGINE_CLIENT_SECRET` — The application's secret; sent as `secret` in the refresh call.
- `PLATFORM_MCP_KUAISHOU_MAGNETIC_ENGINE_REFRESH_TOKEN` — refresh_token from 获取token (auth_code exchange after the advertiser authorised the app); valid 30 days and replaced on every refresh ('刷新后会生成新的 token，老的 access_token 和 refresh_token 将不可再使用'). Set PLATFORM_MCP_STATE_DIR so the rotated token survives restarts.
- `PLATFORM_MCP_KUAISHOU_MAGNETIC_ENGINE_ADVERTISER_ID` — 广告主 ID returned with the access token at authorisation; used by the probe, update_budget and pause_resume.

## Run

    uvx platform-mcp-hub serve kuaishou_magnetic_engine          # Python
    npx -y platform-mcp-hub serve kuaishou_magnetic_engine       # TypeScript
    claude mcp add kuaishou_magnetic_engine -- uvx platform-mcp-hub serve kuaishou_magnetic_engine

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/kuaishou_magnetic_engine-mcp`. Python and TypeScript serve identical tools.
