# 1688 (Alibaba China wholesale) — 一件代发 / 跨境专供 + 1688 Open Platform MCP server

Category: **ecommerce_suppliers** · Docs: https://open.1688.com/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_suppliers/alibaba_1688_open.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /openapi/param2/1/system/currentTime/{client_id}` (https://open.1688.com/doc/signature.htm)
- `list_products` — `POST /openapi/param2/1/com.alibaba.fenxiao.crossborder/product.search.keywordQuery/{client_id}` (https://open.1688.com/api/apidocdetail.htm?id=com.alibaba.fenxiao.crossborder:product.search.keywordQuery-1)
- `get_product` — `POST /openapi/param2/1/com.alibaba.fenxiao.crossborder/product.search.queryProductDetail/{client_id}` (https://open.1688.com/api/apidocdetail.htm?id=com.alibaba.fenxiao.crossborder:product.search.queryProductDetail-1)
- `create_order` — `POST /openapi/param2/1/com.alibaba.trade/alibaba.trade.fastCreateOrder/{client_id}` (https://open.1688.com/api/apidocdetail.htm?id=com.alibaba.trade:alibaba.trade.fastCreateOrder-1)
- `get_order` — `POST /openapi/param2/1/com.alibaba.trade/alibaba.trade.get.buyerView/{client_id}` (https://open.1688.com/api/apidocdetail.htm?id=com.alibaba.trade:alibaba.trade.get.buyerView-1)
- `track` — `POST /openapi/param2/1/com.alibaba.logistics/alibaba.trade.getLogisticsTraceInfo.buyerView/{client_id}` (https://open.1688.com/api/apidocdetail.htm?id=com.alibaba.logistics:alibaba.trade.getLogisticsTraceInfo.buyerView-1)
- ~~`quote_shipping`~~ not offered: Freight is computed inside order preview (alibaba.createOrder.preview) from a full receiver address and cargo list; there is no per-product/country freight quote in the cross-border product or trade APIs (https://open.1688.com/api/apidocdetail.htm?id=com.alibaba.trade:alibaba.trade.fastCreateOrder-1: '系统默认选择最优惠下单方式').

## Credentials

- `PLATFORM_MCP_ALIBABA_1688_OPEN_CLIENT_ID` — appKey of your 1688 Open Platform app (it is also the last URL path segment of every call).
- `PLATFORM_MCP_ALIBABA_1688_OPEN_CLIENT_SECRET` — appSecret of the same app; signs every call (_aop_signature = uppercase hex HMAC-SHA1 over the urlPath from 'param2' + sorted name+value, https://open.1688.com/doc/signature.htm) and refreshes tokens.
- `PLATFORM_MCP_ALIBABA_1688_OPEN_REFRESH_TOKEN` — refresh_token from the OAuth getToken exchange (need_refresh_token=true, https://open.1688.com/doc/apiAuth.htm); valid for the service subscription period (up to half a year). Access tokens (10 hours) are minted from it.
- `PLATFORM_MCP_ALIBABA_1688_OPEN_LANGUAGE` — Language of translated titles for search and product detail (country: en, ja, ko, es, …; see the API's developer reference).
- `PLATFORM_MCP_ALIBABA_1688_OPEN_ORDER_FLOW` — fastCreateOrder flow: general (wholesale order), saleproxy / fenxiao (一件代发 dropshipping order; the seller must have authorised proxy sales), boutiquefenxiao, …

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve alibaba_1688_open   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve alibaba_1688_open
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve alibaba_1688_open   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/alibaba_1688_open-mcp`. Python and TypeScript serve identical tools.
