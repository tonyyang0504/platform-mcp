# Zhubajie (猪八戒) MCP server

Category: **marketplaces** · Docs: https://open.zbj.com/api/apiIndex · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/marketplaces/zhubajie.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /router` (https://open.zbj.com/api/apiDetailIndex?methodId=15&groupId=3)
- `list_products` — `GET /router` (https://open.zbj.com/api/apiDetailIndex?methodId=22&groupId=8)
- `list_sales` — `GET /router` (https://open.zbj.com/api/apiDetailIndex?methodId=18&groupId=4)
- `list_refunds` — `GET /router` (https://open.zbj.com/api/apiDetailIndex?methodId=84&groupId=4)
- ~~`get_product`~~ not offered: zbj.service.getServiceDetail (serviceId + openid, https://open.zbj.com/api/apiDetailIndex?methodId=38&groupId=8) answers subject, amount, content, categories and cases but does not echo the service id, which the vocabulary's product record requires; use list_products (which carries serviceId, subject, amount, state and serviceurl).
- ~~`create_product`~~ not offered: zbj.service.addService (https://open.zbj.com/api/apiDetailIndex?methodId=72&groupId=8) requires a third-level categoryId (from zbj.user.getCategoryByUserId), a cover imgurl uploaded through zbj.services.uploadCoverPic, separate PC and app prices and contents and a unit, none of which the vocabulary carries, and its success response ({successful: true}) returns no service id.
- ~~`update_price`~~ not offered: The only way to change a service's price is zbj.service.editService (https://open.zbj.com/api/apiDetailIndex?methodId=74&groupId=8), a full replacement that requires subject, amount, amountApp, unit, imgurl, cont, contApp and categoryId together; there is no price-only call (zbj.trade.sellerEditAmount changes the amount of one hire/purchase trade, not a listing).
- ~~`get_sales_stats`~~ not offered: No revenue or totals method is documented: the 交易API group (https://open.zbj.com/api/apiIndex) lists trades, refunds and workflow steps only.
- ~~`refund`~~ not offered: The 服务商 cannot issue a refund through the API: refunds are requested by the employer, and the 交易API group (https://open.zbj.com/api/apiIndex) only reads them (zbj.trade.getRefundList).

## Credentials

- `PLATFORM_MCP_ZHUBAJIE_APP_KEY` — appKey (应用证书) of your approved ZOP application (open.zbj.com > 控制台).
- `PLATFORM_MCP_ZHUBAJIE_APP_SECRET` — Application secret (应用密钥); signs every call as uppercase hex SHA1 of secret + params sorted by name + secret (签名算法). Never sent on the wire.
- `PLATFORM_MCP_ZHUBAJIE_ACCESS_TOKEN` — accessToken (访问令牌) from the ZOP OAuth2.0 authorisation of your 猪八戒 服务商 account (https://open.zbj.com/wiki/getWikiCategoryAll?wikiId=8): valid 7 days by default (refresh at http://openapi.zbj.com/oauth2/refreshtoken), or for the purchase period for 工具市场 apps.
- `PLATFORM_MCP_ZHUBAJIE_OPENID` — Your 猪八戒 openid (用户唯一标识, returned with the access token by the ZOP OAuth2.0 authorisation); every service-provider method takes it.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve zhubajie   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve zhubajie
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve zhubajie   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/zhubajie-mcp`. Python and TypeScript serve identical tools.
