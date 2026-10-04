# TVCMALL MCP server

Category: **ecommerce_suppliers** · Docs: https://tvcmall.apifox.cn/ · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_suppliers/tvcmall.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /OpenApi/Category/GetChildren` (https://tvcmall.apifox.cn/api-162165277.md)
- `get_product` — `GET /OpenApi/Product/Detail` (https://tvcmall.apifox.cn/api-162165280.md)
- `quote_shipping` — `POST /order/shippingcost` (https://tvcmall.apifox.cn/api-162165289.md)
- `get_order` — `GET /order/Info` (https://tvcmall.apifox.cn/api-162165288.md)
- ~~`list_products`~~ not offered: GET /OpenApi/Product/Search pages by cursor: lastProductId is 'Required for all request but the first one. The biggest ProductId you get in previous request.' There is no page number or keyword parameter, so the vocabulary's page/query cannot drive it (a page 2 request would repeat page 1).
- ~~`create_order`~~ not offered: POST /order/AddOrder and POST /order/bulkadd take `skus` as one string 'Fomart:<SKU>*<Quantity>, separated by comma'; the runtime cannot join the vocabulary's items array into that string.
- ~~`track`~~ not offered: No tracking-events endpoint; tracking numbers are the Trackingnumbers[] array of GET /order/Info (see get_order).

## Credentials

- `PLATFORM_MCP_TVCMALL_AUTHORIZATION_TOKEN` — AuthorizationToken returned by GET https://openapi.tvc-mall.com/Authorization/GetAuthorization?email=…&password=… once your account manager has enabled the OPEN API (1-3 working days). Sent as `Authorization: TVC <token>` ('The authorization string must start with the prefix "TVC"').

## Run

    uvx platform-mcp-hub serve tvcmall          # Python
    npx -y platform-mcp-hub serve tvcmall       # TypeScript
    claude mcp add tvcmall -- uvx platform-mcp-hub serve tvcmall

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/tvcmall-mcp`. Python and TypeScript serve identical tools.
