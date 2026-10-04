# Coupang MCP server

Category: **ecommerce_channels** · Docs: https://developers.coupang.com/hc/en · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_channels/coupang.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /v2/providers/seller_api/apis/api/v1/marketplace/seller-products` (https://developers.coupang.com/ko/api/products/product-list-paging-query)
- `update_listing` — `PUT /v2/providers/seller_api/apis/api/v1/marketplace/vendor-items/{listing_id}/prices/{price}` (https://developers.coupang.com/ko/api/products/changing-price-of-each-item-of-a-product)
- `set_inventory` — `PUT /v2/providers/seller_api/apis/api/v1/marketplace/vendor-items/{listing_id}/quantities/{quantity}` (https://developers.coupang.com/ko/api/products/changing-quantity-of-each-product-item)
- `end_listing` — `PUT /v2/providers/seller_api/apis/api/v1/marketplace/vendor-items/{listing_id}/sales/stop` (https://developers.coupang.com/ko/api/products/suspend-sale-of-each-item-of-a-product)
- ~~`create_listing`~~ not offered: Product creation (POST /v2/providers/seller_api/apis/api/v1/marketplace/seller-products, https://developers.coupang.com/ko/api/products/product-creation) needs displayCategoryCode, brand, delivery/return settings (outbound shipping place code, return center), required category notices and attributes per item; the vocabulary carries none of them, and new products go through Coupang approval.
- ~~`list_orders`~~ not offered: GET /v2/providers/openapi/apis/api/v5/vendors/{vendorId}/ordersheets requires createdAtFrom AND createdAtTo ("yyyy-mm-dd+09:00", at most 31 days apart) and a single status (https://developers.coupang.com/ko/api/shipments/po-list-query-paging-by-day); the vocabulary has only `since` and no way to derive the required end date.
- ~~`mark_shipped`~~ not offered: Invoice upload (POST /v2/providers/openapi/apis/api/v4/vendors/{vendorId}/orders/invoices) requires per line shipmentBoxId, vendorItemId, deliveryCompanyCode, splitShipping and preSplitShipped besides orderId and invoiceNumber (https://developers.coupang.com/ko/api/shipments/uploading-waybills); shipmentBoxId and vendorItemId are not vocabulary inputs.

## Credentials

- `PLATFORM_MCP_COUPANG_ACCESS_KEY` — Coupang Open API Access Key issued in WING (판매자정보 > 추가판매정보 > OPEN API 키 발급) after business verification; calls must come from one of the (up to 10) allow-listed IPs, and keys expire and must be re-issued.
- `PLATFORM_MCP_COUPANG_SECRET_KEY` — The matching Secret Key: signs every request (HMAC-SHA256 hex over signed-date + method + path + query, sent as `Authorization: CEA algorithm=HmacSHA256, access-key=..., signed-date=..., signature=...`). Never sent on the wire.
- `PLATFORM_MCP_COUPANG_VENDOR_ID` — Coupang vendorId (업체코드, e.g. A00012345), shown in WING after login; used by the probe.

## Run

    uvx platform-mcp-hub serve coupang          # Python
    npx -y platform-mcp-hub serve coupang       # TypeScript
    claude mcp add coupang -- uvx platform-mcp-hub serve coupang

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/coupang-mcp`. Python and TypeScript serve identical tools.
