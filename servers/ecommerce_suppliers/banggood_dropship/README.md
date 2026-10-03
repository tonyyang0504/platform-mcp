# Banggood Dropship Center MCP server

Category: **ecommerce_suppliers** · Docs: https://www.banggood.com/help_center/question_category.html · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_suppliers/banggood_dropship.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /common/getCountries` (https://api.banggood.com/index.php?com=document&article_id=23)
- `list_products` — `GET /product/getProductList` (https://api.banggood.com/index.php?com=document&article_id=10)
- `get_product` — `GET /product/getProductInfo` (https://api.banggood.com/index.php?com=document&article_id=11)
- `quote_shipping` — `GET /product/getShipments` (https://api.banggood.com/index.php?com=document&article_id=12)
- `get_order` — `GET /order/getOrderInfo` (https://api.banggood.com/index.php?com=document&article_id=15)
- `track` — `GET /order/getTrackInfo` (https://api.banggood.com/index.php?com=document&article_id=16)
- ~~`create_order`~~ not offered: POST /order/importOrder is a form post of PHP-style nested arrays (product_list[0][product_id], [warehouse], [poa_id], [shipmethod_code], ... per line, plus product_total; see the official PHP sample https://api.banggood.com/download/banggoodAPI.php.zip); the runtime's form body cannot expand an items array of arbitrary length into indexed bracket keys, and imported orders are then paid in the Banggood web ApiOrderList page.

## Credentials

- `PLATFORM_MCP_BANGGOOD_DROPSHIP_APP_ID` — app_id issued by the Banggood Open Platform (https://api.banggood.com, Manager Center) after the partner application is approved; calls must come from the registered IP address.
- `PLATFORM_MCP_BANGGOOD_DROPSHIP_APP_SECRET` — The app_secret. GET /getAccessToken?app_id=&app_secret= returns an access_token valid 2 hours, sent as the access_token query parameter and renewed automatically.
- `PLATFORM_MCP_BANGGOOD_DROPSHIP_WAREHOUSE` — Banggood warehouse code for quote_shipping (the `warehouse` of GetProductInfo's warehouse_list, e.g. CN, US, UK); the API rejects the call (12031) when it is missing.
- `PLATFORM_MCP_BANGGOOD_DROPSHIP_CURRENCY` — Currency for prices and shipping fees (e.g. USD); Banggood uses USD when unset.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve banggood_dropship   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve banggood_dropship
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve banggood_dropship   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/banggood_dropship-mcp`. Python and TypeScript serve identical tools.
