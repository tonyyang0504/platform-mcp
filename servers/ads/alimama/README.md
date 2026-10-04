# 阿里妈妈 Alimama MCP server

Category: **ads** · Docs: https://open.taobao.com/api.htm?docId=68584&docType=2 · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/alimama.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /router/rest` (https://open.taobao.com/api.htm?docId=68735&docType=2)
- `list_campaigns` — `GET /router/rest` (https://open.taobao.com/api.htm?docId=68584&docType=2)
- `get_report` — `GET /router/rest` (https://open.taobao.com/api.htm?docId=68794&docType=2)
- `update_budget` — `GET /router/rest` (https://open.taobao.com/api.htm?docId=68722&docType=2)
- `pause_resume` — `GET /router/rest` (https://open.taobao.com/api.htm?docId=70473&docType=2)
- ~~`list_accounts`~~ not offered: The 万相台无界 API works on the shop whose seller authorised the session; its account calls report balances (taobao.universalbp.new.account.get.balance), usable scenes (…account.get.can.use.bizcode) and whether the shop is a 无界 user, but none lists ad accounts (https://open.taobao.com/api.htm?docId=68584&docType=2, 万相台无界API group).

## Credentials

- `PLATFORM_MCP_ALIMAMA_APP_KEY` — AppKey of a 淘宝开放平台 application granted the 阿里妈妈 万相台无界 API permission (https://open.taobao.com).
- `PLATFORM_MCP_ALIMAMA_APP_SECRET` — AppSecret of that application; never sent, used for the MD5 request signature.
- `PLATFORM_MCP_ALIMAMA_SESSION` — Seller session key (授权信息 'session') issued when the merchant authorised the app through the TOP OAuth flow (https://open.taobao.com/doc.htm?docId=101617&docType=1: session is required for APIs marked 需要授权); renew it by re-authorising when it expires.
- `PLATFORM_MCP_ALIMAMA_BIZ_CODE` — 万相台无界 scene code (api业务线编码) sent in top_service_context, e.g. onebpDisplay (人群推广), onebpSearch (关键词推广) or onebpSite (全站推广); taobao.universalbp.new.account.get.can.use.bizcode lists the codes the account may use.

## Run

    uvx platform-mcp-hub serve alimama          # Python
    npx -y platform-mcp-hub serve alimama       # TypeScript
    claude mcp add alimama -- uvx platform-mcp-hub serve alimama

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/alimama-mcp`. Python and TypeScript serve identical tools.
