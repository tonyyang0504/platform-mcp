# Taobao MCP server

Category: **marketplaces** · Docs: https://open.taobao.com · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/marketplaces/taobao.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /router/rest` (https://open.taobao.com/api.htm?docType=2&docId=21349)
- `list_products` — `GET /router/rest` (https://open.taobao.com/api.htm?docType=2&docId=18)
- `get_product` — `GET /router/rest` (https://open.taobao.com/api.htm?docType=2&docId=24625)
- `list_sales` — `GET /router/rest` (https://open.taobao.com/api.htm?docType=2&docId=46)
- `list_refunds` — `GET /router/rest` (https://open.taobao.com/api.htm?docType=2&docId=52)
- ~~`create_product`~~ not offered: Publishing needs the category-specific schema flow (alibaba.item.publish.schema.get → alibaba.item.publish.submit, listed in the 商品API group of https://open.taobao.com/api.htm?docId=18&docType=2) with category, properties, SKUs and images; a name + price + currency cannot form a valid item.
- ~~`update_price`~~ not offered: The 商品API group (https://open.taobao.com/api.htm?docId=18&docType=2) offers taobao.item.sku.price.update (needs the SKU properties/sku_id) and tmall.item.price.update (Tmall stores only); there is no plain item-price call for a Taobao item id.
- ~~`get_sales_stats`~~ not offered: No aggregated sales-statistics API is in the TOP 交易API / 商品API groups (https://open.taobao.com/api.htm?docId=46&docType=2); revenue must be summed from trades.
- ~~`refund`~~ not offered: TOP refunds are buyer-initiated: taobao.refunds.receive.get (https://open.taobao.com/api.htm?docId=52&docType=2) lists requests such as 'WAIT_SELLER_AGREE(买家已经申请退款，等待卖家同意)' that the seller answers; there is no call for a seller to refund an arbitrary amount on a trade.

## Credentials

- `PLATFORM_MCP_TAOBAO_APP_KEY` — AppKey of your Taobao Open Platform (TOP) application (open.taobao.com console).
- `PLATFORM_MCP_TAOBAO_APP_SECRET` — AppSecret of the same application; signs every call as upper-case MD5(secret + parameters sorted by name as name+value + secret) and is never sent.
- `PLATFORM_MCP_TAOBAO_SESSION` — The seller's authorised session (access_token) from the TOP user-authorisation flow (https://open.taobao.com/doc.htm?docId=102635&docType=1); sent as the `session` parameter. Update it when it expires — the runtime does not refresh it.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve taobao   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve taobao
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve taobao   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/taobao-mcp`. Python and TypeScript serve identical tools.
