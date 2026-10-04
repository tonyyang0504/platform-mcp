# JD Worldwide (京东全球购) + JD Open Platform (宙斯) MCP server

Category: **ecommerce_suppliers** · Docs: https://jos.jd.com/apilist · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_suppliers/jd_worldwide_open.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /routerjson` (https://jos.jd.com/apilist?apiGroupId=41&apiId=12865&apiName=jingdong.seller.vender.info.get)
- `list_products` — `GET /routerjson` (https://jos.jd.com/apilist?apiGroupId=86&apiId=13568&apiName=jingdong.ware.read.searchWare4Valid)
- `get_product` — `GET /routerjson` (https://jos.jd.com/apilist?apiGroupId=86&apiId=13320&apiName=jingdong.ware.read.findWareById)
- `get_order` — `GET /routerjson` (https://jos.jd.com/apilist?apiGroupId=107&apiId=15661&apiName=jingdong.pop.order.get)
- ~~`quote_shipping`~~ not offered: The JOS product and order API groups (https://jos.jd.com/apilist?apiGroupId=86, apiGroupId=107) serve the merchant's own shop; there is no buyer-side freight quote — freight templates (jingdong.SkuFareTemplateService.getTemplates) describe the merchant's own shipping rules.
- ~~`create_order`~~ not offered: Orders are placed by JD shoppers; the order API group ('订单API组(该组下所有接口均不支持自营店铺业务)', https://jos.jd.com/apilist?apiGroupId=107) searches, ships and edits received orders, with no merchant-side order creation for sourcing.
- ~~`track`~~ not offered: Shipment tracking is part of JD Logistics (京东物流) APIs that need a separate logistics customer account; for a merchant order the waybill number is returned by get_order (orderInfo.waybill).

## Credentials

- `PLATFORM_MCP_JD_WORLDWIDE_OPEN_APP_KEY` — app_key of your JD Open Platform (宙斯/JOS) app, https://jos.jd.com/.
- `PLATFORM_MCP_JD_WORLDWIDE_OPEN_APP_SECRET` — appSecret of the same app; signs every call: upper(MD5(appSecret + sorted name+value of all parameters + appSecret)). Never sent on the wire.
- `PLATFORM_MCP_JD_WORLDWIDE_OPEN_ACCESS_TOKEN` — The merchant's access_token from the JOS OAuth authorisation (https://jos.jd.com/commondoc?listId=32); renew it before it expires and update this value — the runtime does not refresh it.

## Run

    uvx platform-mcp-hub serve jd_worldwide_open          # Python
    npx -y platform-mcp-hub serve jd_worldwide_open       # TypeScript
    claude mcp add jd_worldwide_open -- uvx platform-mcp-hub serve jd_worldwide_open

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/jd_worldwide_open-mcp`. Python and TypeScript serve identical tools.
