# Coupang Wing (seller) + Coupang Open API MCP server

Category: **ecommerce_suppliers** · Docs: https://developers.coupang.com/ko/api · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_suppliers/coupang_open_api.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /v2/providers/seller_api/apis/api/v1/marketplace/seller-products` (https://developers.coupang.com/ko/api/products/product-list-paging-query)
- `list_products` — `GET /v2/providers/seller_api/apis/api/v1/marketplace/seller-products` (https://developers.coupang.com/ko/api/products/product-list-paging-query)
- `get_product` — `GET /v2/providers/seller_api/apis/api/v1/marketplace/seller-products/{id}` (https://developers.coupang.com/ko/api/products/querying-product)
- `get_order` — `GET /v2/providers/openapi/apis/api/v5/vendors/{vendor_id}/{id}/ordersheets` (https://developers.coupang.com/ko/api/shipments/single-po-query-using-orderid)
- `track` — `GET /v2/providers/openapi/apis/api/v5/vendors/{vendor_id}/{order_id}/ordersheets` (https://developers.coupang.com/ko/api/shipments/single-po-query-using-orderid)
- ~~`create_order`~~ not offered: Seller-side API: customers order on coupang.com; the Open API only processes those orders (상품준비중, 운송장 업로드) and cannot place one.
- ~~`quote_shipping`~~ not offered: No shipping-rate endpoint: delivery charges are fields of the seller's own listing (deliveryChargeType, deliveryCharge), not a quote for a destination.

## Credentials

- `PLATFORM_MCP_COUPANG_OPEN_API_ACCESS_KEY` — Coupang Open API Access Key issued in WING (판매자정보 > 추가판매정보 > OPEN API 키 발급) after business verification; calls must come from one of the (up to 10) allow-listed IPs, and keys expire and must be re-issued.
- `PLATFORM_MCP_COUPANG_OPEN_API_SECRET_KEY` — The matching Secret Key: signs every request (HMAC-SHA256 hex over signed-date + method + path + query, sent as `Authorization: CEA algorithm=HmacSHA256, access-key=..., signed-date=..., signature=...`). Never sent on the wire.
- `PLATFORM_MCP_COUPANG_OPEN_API_VENDOR_ID` — Coupang vendorId (업체코드, e.g. A00012345), shown in WING after login; used in every path/query.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve coupang_open_api   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve coupang_open_api
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve coupang_open_api   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/coupang_open_api-mcp`. Python and TypeScript serve identical tools.
