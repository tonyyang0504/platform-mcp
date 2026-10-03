# Taobao/Tmall distribution (淘宝分销 → Tmall 供销平台) + Taobao Affiliate (淘宝联盟) MCP server

Category: **ecommerce_suppliers** · Docs: https://open.taobao.com/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_suppliers/taobao_fenxiao_alimama.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /router/rest` (https://open.taobao.com/api.htm?docType=2&docId=120)
- `list_products` — `GET /router/rest` (https://open.taobao.com/api.htm?docType=2&docId=64759)
- `get_product` — `GET /router/rest` (https://open.taobao.com/api.htm?docType=2&docId=24518)
- ~~`quote_shipping`~~ not offered: 淘宝联盟 promoters do not buy: the 淘宝客 APIs (https://open.taobao.com/api.htm?docId=64759&docType=2) return promotion links and at most a real_post_fee estimate; freight is quoted by the seller at checkout on Taobao.
- ~~`create_order`~~ not offered: Orders are placed by the buyer on Taobao through the promotion link; no 淘宝客 API creates orders (https://open.taobao.com/api.htm?docId=43328&docType=2 only reports them). Distributor purchase orders of the 供销平台 need a per-member session from the distributor's ISV authorisation.
- ~~`get_order`~~ not offered: taobao.tbk.order.details.get (https://open.taobao.com/api.htm?docId=43328&docType=2) queries promoted orders only by time window (start_time/end_time ≤ 3 h apart), not by order id.
- ~~`track`~~ not offered: No logistics API exists for 淘宝客 promoters (https://open.taobao.com/api.htm?docId=43328&docType=2); shipments belong to the buyer's Taobao order.

## Credentials

- `PLATFORM_MCP_TAOBAO_FENXIAO_ALIMAMA_APP_KEY` — AppKey of your Taobao Open Platform (TOP) application (open.taobao.com console).
- `PLATFORM_MCP_TAOBAO_FENXIAO_ALIMAMA_APP_SECRET` — AppSecret of the same application; signs every call as upper-case MD5(secret + parameters sorted by name as name+value + secret) and is never sent.
- `PLATFORM_MCP_TAOBAO_FENXIAO_ALIMAMA_ADZONE_ID` — Promotion slot id: the last number of your 淘宝联盟 PID mm_xxx_xxx_<adzone_id> (pub.alimama.com > 推广管理 > 推广位管理).

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve taobao_fenxiao_alimama   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve taobao_fenxiao_alimama
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve taobao_fenxiao_alimama   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/taobao_fenxiao_alimama-mcp`. Python and TypeScript serve identical tools.
