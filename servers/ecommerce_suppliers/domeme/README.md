# Domeme (Domeggook dropship / 배송대행 B2B) MCP server

Category: **ecommerce_suppliers** · Docs: https://openapi.domeggook.com/ko/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_suppliers/domeme.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /ssl/api/` (https://openapi.domeggook.com/ko/articles/%EC%83%81%ED%92%88%EB%A6%AC%EC%8A%A4%ED%8A%B8-43780628)
- `list_products` — `GET /ssl/api/` (https://openapi.domeggook.com/ko/articles/%EC%83%81%ED%92%88%EB%A6%AC%EC%8A%A4%ED%8A%B8-43780628)
- `get_product` — `GET /ssl/api/` (https://openapi.domeggook.com/ko/articles/%EC%83%81%ED%92%88%EC%83%81%EC%84%B8%EC%A0%95%EB%B3%B4-933abc24)
- ~~`quote_shipping`~~ not offered: No shipping-rate call: shipping rules are part of the product record (deli.method, deli.pay, deli.dome{type, fee, tbl} quantity tables, see get_product), not quoted per destination.
- ~~`create_order`~~ not offered: Ordering (주문서 생성) is a Private API: 'Private API는 권한 신청 및 승인 후 사용할 수 있습니다' and needs a setLogin session (member id/password, client ip, device 'Third Party' -> sId, https://openapi.domeggook.com/ko/articles/%EB%A1%9C%EA%B7%B8%EC%9D%B8-e4aaf7c2); not mapped for this Open-API key adapter.
- ~~`get_order`~~ not offered: Order lookup (구매 주문서 상세 조회) is a Private API requiring approval and a setLogin session id (sId); not mapped for this Open-API key adapter.
- ~~`track`~~ not offered: Delivery information is part of the Private API purchase-order record (approval + setLogin session required); not mapped.

## Credentials

- `PLATFORM_MCP_DOMEME_API_KEY` — Domeggook Open API key (openapi.domeggook.com > API 키 발급/관리), sent as the `aid` query parameter. The same key serves 도매꾹 and 도매매.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve domeme   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve domeme
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve domeme   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/domeme-mcp`. Python and TypeScript serve identical tools.
