# Yahoo! Shopping (JP) MCP server

Category: **ecommerce_channels** · Docs: https://developer.yahoo.co.jp/webapi/shopping/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_channels/yahoo_shopping_jp.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /ShoppingWebService/V1/stCategoryList` (https://developer.yahoo.co.jp/webapi/shopping/stCategoryList.html)
- `set_inventory` — `POST /ShoppingWebService/V1/setStock` (https://developer.yahoo.co.jp/webapi/shopping/setStock.html)
- `update_listing` — `POST /ShoppingWebService/V1/updateItems` (https://developer.yahoo.co.jp/webapi/shopping/updateItems.html)
- `end_listing` — `POST /ShoppingWebService/V1/updateItems` (https://developer.yahoo.co.jp/webapi/shopping/updateItems.html)
- ~~`create_listing`~~ not offered: 商品登録API (https://developer.yahoo.co.jp/webapi/shopping/editItem.html) overwrites every omitted field with defaults and needs path (store category), product_category and the item's full data; images go through a separate upload API and the item must then be published with 全反映予約API. The vocabulary cannot supply the required fields.
- ~~`list_orders`~~ not offered: 注文検索API (POST /ShoppingWebService/V1/orderList, XML <Req><Search>…, https://developer.yahoo.co.jp/webapi/shopping/orderList.html) is one of the APIs for which, without public-key authentication, "リフレッシュトークンの有効期限は「12時間」に制限されます" (https://developer.yahoo.co.jp/webapi/shopping/help/#aboutapipublickey) — one call would shorten the token for every tool. Public-key authentication needs an X-sws-signature header = Base64(RSA-PKCS1 ENCRYPTION of "sellerId:unixtime" with the store's public key), which the runtime cannot compute (it signs, it does not RSA-encrypt).
- ~~`mark_shipped`~~ not offered: 出荷ステータス変更API (https://developer.yahoo.co.jp/webapi/shopping/orderShipStatusChange.html) is an order API: the same 12-hour refresh-token restriction applies unless each call carries the RSA-encrypted X-sws-signature header, which the runtime cannot produce.

## Credentials

- `PLATFORM_MCP_YAHOO_SHOPPING_JP_CLIENT_ID` — Yahoo! JAPAN Client ID (アプリケーションID) of an app approved for the Shopping store APIs, linked to the store's Business ID.
- `PLATFORM_MCP_YAHOO_SHOPPING_JP_CLIENT_SECRET` — The app's シークレット (sent as HTTP Basic to the YConnect v2 token endpoint).
- `PLATFORM_MCP_YAHOO_SHOPPING_JP_REFRESH_TOKEN` — YConnect v2 refresh token from one authorization-code consent by the store's Yahoo! JAPAN ID (https://developer.yahoo.co.jp/webapi/shopping/help/#accesstoken). It lasts 4 weeks; re-consent afterwards.
- `PLATFORM_MCP_YAHOO_SHOPPING_JP_SELLER_ID` — ストアアカウント (store account id, lower-case letters, digits, - and _).

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve yahoo_shopping_jp   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve yahoo_shopping_jp
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve yahoo_shopping_jp   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/yahoo_shopping_jp-mcp`. Python and TypeScript serve identical tools.
