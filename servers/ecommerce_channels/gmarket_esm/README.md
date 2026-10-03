# Gmarket / Auction (ESM) MCP server

Category: **ecommerce_channels** · Docs: https://etapi.gmarket.com/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_channels/gmarket_esm.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /item/v1/shipping/delivery-company` (https://etapi.gmarket.com/142)
- `list_orders` — `POST /shipping/v1/Order/RequestOrders` (https://etapi.gmarket.com/67)
- `mark_shipped` — `POST /shipping/v1/Delivery/ShippingInfo` (https://etapi.gmarket.com/70)
- `update_listing` — `PUT /item/v1/goods/{listing_id}/price` (https://etapi.gmarket.com/186)
- `set_inventory` — `PUT /item/v1/goods/{listing_id}/stock` (https://etapi.gmarket.com/194)
- `end_listing` — `DELETE /item/v1/goods/{listing_id}` (https://etapi.gmarket.com/29)
- ~~`create_listing`~~ not offered: 상품 등록 API (https://etapi.gmarket.com/20) requires the Gmarket/Auction leaf category codes ('itemBasicInfo > category > site > catCode', Y), shipping place and dispatch-policy numbers ('shipping > policy > placeNo', Y), product-notice codes ('officialNotice > officialNoticeNo', Y), selling periods and isVatFree; the vocabulary's create_listing has none of these inputs, so a valid registration cannot be built.

## Credentials

- `PLATFORM_MCP_GMARKET_ESM_SECRET_KEY` — ESM Trading API Secret Key issued by Gmarket after the e-mail application (etapihelp@gmail.com); signs the HS256 JWT sent as 'Authorization: Bearer <JWT>' on every call. Never sent on the wire.
- `PLATFORM_MCP_GMARKET_ESM_MASTER_ID` — Your ESM+ master id; sent as the JWT header `kid` (selling-tool vendors put their own master id here). https://etapi.gmarket.com/pages/API-가이드
- `PLATFORM_MCP_GMARKET_ESM_SITE_SELLER_IDS` — The JWT `ssi` claim: site id + seller id pairs, e.g. 'A:myauctionid,G:mygmarketid' (A = Auction, G = Gmarket; one of each at most).
- `PLATFORM_MCP_GMARKET_ESM_SITE_TYPE` — Site whose orders list_orders reads: 1 = Auction, 2 = Gmarket (RequestOrders siteType).

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve gmarket_esm   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve gmarket_esm
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve gmarket_esm   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/gmarket_esm-mcp`. Python and TypeScript serve identical tools.
