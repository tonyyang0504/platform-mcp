# AliExpress Dropshipping (DS) API / AliExpress Open Platform MCP server

Category: **ecommerce_suppliers** · Docs: https://openservice.aliexpress.com/doc/doc.htm#/?docId=1646 · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_suppliers/aliexpress_ds.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /sync` (https://openservice.aliexpress.com/doc/api.htm#/api?cid=21038&path=aliexpress.ds.member.benefit.get&methodType=GET/POST)
- `list_products` — `GET /sync` (https://openservice.aliexpress.com/doc/api.htm#/api?cid=21038&path=aliexpress.ds.text.search&methodType=GET/POST)
- `get_product` — `GET /sync` (https://openservice.aliexpress.com/doc/api.htm#/api?cid=21038&path=aliexpress.ds.product.get&methodType=GET/POST)
- `create_order` — `POST /sync` (https://openservice.aliexpress.com/doc/api.htm#/api?cid=21038&path=aliexpress.ds.order.create&methodType=GET/POST)
- `get_order` — `GET /sync` (https://openservice.aliexpress.com/doc/api.htm#/api?cid=21038&path=aliexpress.trade.ds.order.get&methodType=GET/POST)
- `track` — `GET /sync` (https://openservice.aliexpress.com/doc/api.htm#/api?cid=21038&path=aliexpress.ds.order.tracking.get&methodType=GET/POST)
- ~~`quote_shipping`~~ not offered: aliexpress.ds.freight.query (https://openservice.aliexpress.com/doc/doc.htm#/?docId=1597) requires queryDeliveryReq.selectedSkuId ('Selected sku (From aliexpres.product.get)', Required: Yes) besides productId, shipToCountry and quantity; the vocabulary's quote_shipping has no SKU input, so a valid request cannot be built.

## Credentials

- `PLATFORM_MCP_ALIEXPRESS_DS_APP_KEY` — App Key of your AliExpress Open Platform Dropshipping app (Console > App Management; https://openservice.aliexpress.com/doc/doc.htm#/?docId=1589).
- `PLATFORM_MCP_ALIEXPRESS_DS_APP_SECRET` — App Secret of the same app; signs every call (uppercase hex HMAC-SHA256 over the parameters sorted by name as name+value, docId=1386). Never sent on the wire.
- `PLATFORM_MCP_ALIEXPRESS_DS_ACCESS_TOKEN` — Buyer (dropshipper) access_token from the authorization-code exchange /auth/token/create (docId=1592). Production tokens last 30 days (expires_in 2592000); renew with /auth/token/refresh (docId=1593) and update this value — the runtime does not refresh it.
- `PLATFORM_MCP_ALIEXPRESS_DS_SHIP_TO_COUNTRY` — Two-letter destination country used for DS prices, stock and search (countryCode / ship_to_country), e.g. US.
- `PLATFORM_MCP_ALIEXPRESS_DS_CURRENCY` — Currency for search and product prices (currency / target_currency), e.g. USD.
- `PLATFORM_MCP_ALIEXPRESS_DS_LANGUAGE` — Locale for search, product text and tracking (local / target_language / language), e.g. en_US.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve aliexpress_ds   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve aliexpress_ds
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve aliexpress_ds   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/aliexpress_ds-mcp`. Python and TypeScript serve identical tools.
