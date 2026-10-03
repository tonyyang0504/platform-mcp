# Dropshipzone (AU) MCP server

Category: **ecommerce_suppliers** · Docs: https://www.dropshipzone.com.au/apidoc/index.html · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_suppliers/dropshipzone_au.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /v2/categories` (https://www.dropshipzone.com.au/apidoc/index.html#api-Category-V2GetCategory)
- `list_products` — `GET /v2/products` (https://www.dropshipzone.com.au/apidoc/index.html#api-Product-V2GetProducts)
- `get_product` — `GET /v2/products` (https://www.dropshipzone.com.au/apidoc/index.html#api-Product-V2GetProducts)
- `create_order` — `POST /placingOrder` (https://www.dropshipzone.com.au/apidoc/index.html#api-Order-Place_Order)
- `get_order` — `GET /orders` (https://www.dropshipzone.com.au/apidoc/index.html#api-Order-GetHttpsApiDropshipzoneComAuOrders)
- `track` — `GET /orders` (https://www.dropshipzone.com.au/apidoc/index.html#api-Order-GetHttpsApiDropshipzoneComAuOrders)
- ~~`quote_shipping`~~ not offered: POST /v2/get_zone_rates takes skus and returns per-SKU rate tables keyed by Australian zone ({sku, standard{act, nsw_m, nsw_r, ..., nz}, defined{adelaide, brisbane, ...}}) after a postcode -> zone lookup (POST /v2/get_zone_mapping); there is no country-level options list for the product_id/country/quantity shape.

## Credentials

- `PLATFORM_MCP_DROPSHIPZONE_AU_EMAIL` — Dropshipzone API user e-mail; POST /auth {email, password} returns a token valid 15 minutes, sent as `Authorization: jwt <token>` and renewed automatically.
- `PLATFORM_MCP_DROPSHIPZONE_AU_PASSWORD` — Dropshipzone API user password.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve dropshipzone_au   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve dropshipzone_au
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve dropshipzone_au   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/dropshipzone_au-mcp`. Python and TypeScript serve identical tools.
