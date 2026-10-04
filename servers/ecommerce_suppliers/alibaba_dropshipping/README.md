# Alibaba.com Dropshipping / Alibaba Open Platform MCP server

Category: **ecommerce_suppliers** · Docs: https://openapi.alibaba.com/doc/api.htm · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_suppliers/alibaba_dropshipping.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /rest/alibaba/order/list` (https://openapi.alibaba.com/doc/api.htm#/api?cid=8&path=/alibaba/order/list&methodType=GET/POST)
- `list_products` — `GET /rest/eco/buyer/product/search` (https://openapi.alibaba.com/doc/api.htm#/api?cid=7&path=/eco/buyer/product/search&methodType=GET)
- `get_product` — `GET /rest/eco/buyer/product/description` (https://openapi.alibaba.com/doc/api.htm#/api?cid=7&path=/eco/buyer/product/description&methodType=GET)
- `quote_shipping` — `GET /rest/shipping/freight/calculate` (https://openapi.alibaba.com/doc/api.htm#/api?cid=8&path=/shipping/freight/calculate&methodType=GET/POST)
- `create_order` — `POST /rest/buynow/order/create` (https://openapi.alibaba.com/doc/api.htm#/api?cid=8&path=/buynow/order/create&methodType=GET/POST)
- `get_order` — `GET /rest/alibaba/order/get` (https://openapi.alibaba.com/doc/api.htm#/api?cid=8&path=/alibaba/order/get&methodType=GET/POST)
- `track` — `GET /rest/order/logistics/tracking/get` (https://openapi.alibaba.com/doc/api.htm#/api?cid=8&path=/order/logistics/tracking/get&methodType=GET/POST)

## Credentials

- `PLATFORM_MCP_ALIBABA_DROPSHIPPING_APP_KEY` — App Key of your Alibaba.com Open Platform app (https://openapi.alibaba.com/ App Console; admin-reviewed).
- `PLATFORM_MCP_ALIBABA_DROPSHIPPING_APP_SECRET` — App Secret of the same app; signs every call: uppercase hex HMAC-SHA256 over the API path without '/rest' (e.g. /alibaba/order/get) + the parameters sorted by name as name+value (docId=61). Never sent on the wire.
- `PLATFORM_MCP_ALIBABA_DROPSHIPPING_ACCESS_TOKEN` — access_token from the authorisation-code exchange /auth/token/create (https://openapi.alibaba.com/doc/api.htm#/api?cid=4&path=/auth/token/create). It expires after expires_in seconds; renew it with /auth/token/refresh (a signed call) and update this value — the runtime does not refresh it.
- `PLATFORM_MCP_ALIBABA_DROPSHIPPING_SHIP_TO_COUNTRY` — Two-letter destination country used for product search and cost prices (shipToCountry / ship_to_country), e.g. US.
- `PLATFORM_MCP_ALIBABA_DROPSHIPPING_CURRENCY` — ISO 4217 currency for search results and product prices, e.g. USD.

## Run

    uvx platform-mcp-hub serve alibaba_dropshipping          # Python
    npx -y platform-mcp-hub serve alibaba_dropshipping       # TypeScript
    claude mcp add alibaba_dropshipping -- uvx platform-mcp-hub serve alibaba_dropshipping

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/alibaba_dropshipping-mcp`. Python and TypeScript serve identical tools.
