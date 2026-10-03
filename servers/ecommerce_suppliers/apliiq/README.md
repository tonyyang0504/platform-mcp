# Apliiq MCP server

Category: **ecommerce_suppliers** · Docs: https://help.apliiq.com/portal/en/kb/help/api · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_suppliers/apliiq.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /v1/Order` (https://help.apliiq.com/portal/en/kb/articles/get-order)
- `list_products` — `GET /v1/Product` (https://help.apliiq.com/portal/en/kb/articles/product-api)
- `get_product` — `GET /v1/Product/{id}` (https://help.apliiq.com/portal/en/kb/articles/product-api)
- `get_order` — `GET /v1/Order/{id}` (https://help.apliiq.com/portal/en/kb/articles/get-order)
- `track` — `GET /v1/Order/{order_id}` (https://help.apliiq.com/portal/en/kb/articles/get-order)
- ~~`create_order`~~ not offered: POST /v1/Order must be signed over base64(request body) ('base64_encode(HMACSHA256([APPId][RTS][STATE][Base64_ReqContent]...))', https://help.apliiq.com/portal/en/kb/articles/authentication); the runtime's signing templates have {body} but no base64 transform of it, so a POST cannot be signed.
- ~~`quote_shipping`~~ not offered: No shipping-rate endpoint is documented in the Apliiq API sections (Orders, Products, Warehouse, Add to store).

## Credentials

- `PLATFORM_MCP_APLIIQ_APP_ID` — API Key (APPID) of an Apliiq custom store (https://www.apliiq.com/verified/stores > custom store > API Key).
- `PLATFORM_MCP_APLIIQ_SHARED_SECRET` — The store's Shared_SECRET: signs every request (base64 HMAC-SHA256 over APPID + RTS + STATE + base64(body), empty for GET). Never sent on the wire.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve apliiq   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve apliiq
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve apliiq   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/apliiq-mcp`. Python and TypeScript serve identical tools.
