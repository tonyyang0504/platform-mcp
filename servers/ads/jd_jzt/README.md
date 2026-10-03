# 京准通 JD JZT MCP server

Category: **ads** · Docs: https://opendoc.jd.com/ads_api/jzt/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ads/jd_jzt.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /routerjson` (https://opendoc.jd.com/ads_api/jzt/api/word/kuaiche/campaign/list.html)
- `list_campaigns` — `GET /routerjson` (https://opendoc.jd.com/ads_api/jzt/api/word/kuaiche/campaign/list.html)
- `update_budget` — `GET /routerjson` (https://opendoc.jd.com/ads_api/jzt/api/word/kuaiche/campaign/updateBudget.html)
- `pause_resume` — `GET /routerjson` (https://opendoc.jd.com/ads_api/jzt/api/word/kuaiche/campaign/updateStatus.html)
- ~~`list_accounts`~~ not offered: The 京准通 API acts for the PIN that authorised the access_token; the only account-listing calls are for agencies and sub-accounts ('查询代理子PIN列表', '查询子账号列表' under 账户管理, https://opendoc.jd.com/ads_api/jzt/), not the advertiser's own ad accounts.
- ~~`get_report`~~ not offered: The cross-channel 自定义报表 (jingdong.ads.ibg.UniversalJosService.custom.query.v2, https://opendoc.jd.com/ads_api/jzt/api/word/report/datacenter/custom/query.html) is in gray release: '当前为灰度发布阶段，如需使用，请发送邮件至org.ads.api1@jd.com申请'; list_campaigns already returns today's cost, clicks, impressions and orders per campaign.

## Credentials

- `PLATFORM_MCP_JD_JZT_APP_KEY` — app_key of the JOS (京东宙斯) application approved for the 京准通 API permission package (https://opendoc.jd.com/ads_api/jzt/api/word/settle.html).
- `PLATFORM_MCP_JD_JZT_APP_SECRET` — appSecret of that application; never sent, used for the MD5 request signature.
- `PLATFORM_MCP_JD_JZT_ACCESS_TOKEN` — OAuth access_token of the 京准通 PIN that authorised the app (https://jos.jd.com/commondoc?listId=32); renew it through the JOS authorisation flow when it expires.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve jd_jzt   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve jd_jzt
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve jd_jzt   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/jd_jzt-mcp`. Python and TypeScript serve identical tools.
