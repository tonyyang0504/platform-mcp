# Digistore24 MCP server

Category: **marketplaces** · Docs: https://dev.digistore24.com · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/marketplaces/digistore24.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /getUserInfo` (https://digistore24.com/api/docs/paths/getUserInfo.yaml)
- `list_products` — `GET /listProducts` (https://digistore24.com/api/docs/paths/listProducts.yaml)
- `get_product` — `GET /getProduct` (https://digistore24.com/api/docs/paths/getProduct.yaml)
- `create_product` — `POST /createProduct` (https://digistore24.com/api/docs/paths/createProduct.yaml)
- `update_price` — `POST /createPaymentplan` (https://digistore24.com/api/docs/paths/createPaymentplan.yaml)
- `list_sales` — `GET /listPurchases` (https://digistore24.com/api/docs/paths/listPurchases.yaml)
- `get_sales_stats` — `GET /statsSales` (https://digistore24.com/api/docs/paths/statsSales.yaml)
- `list_refunds` — `GET /listTransactions` (https://digistore24.com/api/docs/paths/listTransactions.yaml)
- `refund` — `POST /refundPurchase` (https://digistore24.com/api/docs/paths/refundPurchase.yaml)

## Credentials

- `PLATFORM_MCP_DIGISTORE24_API_KEY` — Digistore24 API key (vendor view > Settings > Account access > API keys; a writable / Full access key for create_product, update_price and refund, read-only suffices for the rest) sent as the X-DS-API-KEY header. The staging host https://www.digitest24.de/api/call is not switched to.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve digistore24   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve digistore24
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve digistore24   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/digistore24-mcp`. Python and TypeScript serve identical tools.
