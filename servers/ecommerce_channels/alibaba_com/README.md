# Alibaba.com MCP server

Category: **ecommerce_channels** · Docs: https://openapi.alibaba.com/doc/doc.htm · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_channels/alibaba_com.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /rest/alibaba/order/list` (https://openapi.alibaba.com/doc/api.htm#/api?cid=8&path=/alibaba/order/list&methodType=GET/POST)
- `list_orders` — `GET /rest/alibaba/order/list` (https://openapi.alibaba.com/doc/api.htm#/api?cid=8&path=/alibaba/order/list&methodType=GET/POST)
- `set_inventory` — `POST /rest/icbu/product/edit-inventory` (https://openapi.alibaba.com/doc/api.htm#/api?cid=11&path=/icbu/product/edit-inventory&methodType=GET/POST)
- `update_listing` — `POST /rest/icbu/product/edit-price` (https://openapi.alibaba.com/doc/api.htm#/api?cid=11&path=/icbu/product/edit-price&methodType=GET/POST)
- `end_listing` — `POST /rest/alibaba/icbu/product/batch/update/status` (https://openapi.alibaba.com/doc/api.htm#/api?cid=11&path=/alibaba/icbu/product/batch/update/status&methodType=GET/POST)
- ~~`create_listing`~~ not offered: Products are published through /icbu/product/schema/add, which takes the category's JSON schema document ('/alibaba/icbu/product/schema/get' first, https://openapi.alibaba.com/doc/api.htm#/api?cid=1&path=/icbu/product/schema/add&methodType=GET/POST); the vocabulary's title/price/quantity inputs cannot fill a category schema.
- ~~`mark_shipped`~~ not offered: Ggs one Order Shipping (/alibaba/v2/order/shipping, https://openapi.alibaba.com/doc/api.htm#/api?cid=12&path=/alibaba/v2/order/shipping&methodType=GET/POST) requires 'logistics_type' (Required, documented only as 'Logistics Type', no values listed) and a 'service_provider' code from alibaba.seller.order.shipping.channels; a valid request cannot be built from order_id/carrier/tracking_number.

## Credentials

- `PLATFORM_MCP_ALIBABA_COM_APP_KEY` — App Key of your Alibaba.com Open Platform app (https://openapi.alibaba.com/ App Console; admin-reviewed).
- `PLATFORM_MCP_ALIBABA_COM_APP_SECRET` — App Secret of the same app; signs every call: uppercase hex HMAC-SHA256 over the API path without '/rest' (e.g. /alibaba/order/get) + the parameters sorted by name as name+value (docId=61). Never sent on the wire.
- `PLATFORM_MCP_ALIBABA_COM_ACCESS_TOKEN` — access_token from the authorisation-code exchange /auth/token/create (https://openapi.alibaba.com/doc/api.htm#/api?cid=4&path=/auth/token/create). It expires after expires_in seconds; renew it with /auth/token/refresh (a signed call) and update this value — the runtime does not refresh it.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve alibaba_com   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve alibaba_com
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve alibaba_com   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/alibaba_com-mcp`. Python and TypeScript serve identical tools.
