# SHEIN Marketplace MCP server

Category: **ecommerce_channels** · Docs: https://open.sheincorp.com/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_channels/shein.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /open-api/msc/warehouse/list` (https://open.sheincorp.com/documents/apidoc/detail/3002013)
- `list_orders` — `POST /open-api/order/order-list` (https://open.sheincorp.com/documents/apidoc/detail/3001921)
- `set_inventory` — `POST /open-api/stock/change-inventory/v2` (https://open.sheincorp.com/documents/apidoc/detail/3001738)
- `update_listing` — `POST /open-api/openapi-business-backend/product/price/save` (https://open.sheincorp.com/documents/apidoc/detail/3001940)
- `end_listing` — `POST /open-api/goods/modify-skc-shelf` (https://open.sheincorp.com/documents/apidoc/detail/3001939)
- ~~`create_listing`~~ not offered: 商品发布/编辑 (/open-api/goods/product/publishOrEdit, https://open.sheincorp.com/documents/apidoc/detail/3002018) needs the leaf category, attribute template values, brand, SKC/SKU structures and images uploaded through /open-api/goods/transform-pic; the vocabulary's create_listing inputs cannot build it.
- ~~`mark_shipped`~~ not offered: 批量上传运单号 (https://open.sheincorp.com/documents/apidoc/detail/3001274) requires per-item 'goodsId' (required; 'each piece has a different goodsId, obtained from the order detail API') and an 'expressIdCode' from the ship-channel query; mark_shipped has only order_id, carrier and tracking_number.

## Credentials

- `PLATFORM_MCP_SHEIN_OPEN_KEY_ID` — openKeyId returned by the store-authorisation call /open-api/auth/get-by-token (Store Authorization Application Manual); sent as x-lt-openKeyId.
- `PLATFORM_MCP_SHEIN_SIGN_KEY` — The HMAC key SHEIN's Signature Rules define as SecretKey + RandomKey: the DECRYPTED secretKey from /open-api/auth/get-by-token (it is returned AES-encrypted with your appSecretKey; decrypt it once as the authorisation manual shows) immediately followed by your random_key, e.g. '6BEC9C4B668B4B14B17EEF106BB98AE5test1'. Never sent on the wire.
- `PLATFORM_MCP_SHEIN_RANDOM_KEY` — The 5-character RandomKey you choose (letters/digits, e.g. 'test1'); it prefixes every x-lt-signature and must equal the last 5 characters of sign_key.
- `PLATFORM_MCP_SHEIN_SITE` — SHEIN sub-site for price and shelf changes, e.g. shein-us, shein-mx, shein-fr (店铺站点和币种信息 /open-api/openapi-business-backend/site/query).
- `PLATFORM_MCP_SHEIN_CURRENCY` — Selling currency of that site for price changes, e.g. USD, MXN, EUR.
- `PLATFORM_MCP_SHEIN_WAREHOUSE_CODE` — Merchant warehouse code (from `me`) for stock updates; required when the store has several warehouses.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve shein   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve shein
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve shein   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/shein-mcp`. Python and TypeScript serve identical tools.
