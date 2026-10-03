# Peecho (Prodigi Group) MCP server

Category: **ecommerce_suppliers** · Docs: https://www.peecho.com/print-api-documentation · Verified: 2026-09-25

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_suppliers/peecho.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /offering/list` (https://peechoapiv3.docs.apiary.io/)
- `quote_shipping` — `POST /quote` (https://peechoapiv3.docs.apiary.io/)
- `create_order` — `POST /order/` (https://peechoapiv3.docs.apiary.io/)
- `get_order` — `GET /order/details` (https://peechoapiv3.docs.apiary.io/)
- ~~`list_products`~~ not offered: GET /offering/list answers offerings nested under category and sub-category code keys ({"BO": {"SC": [...]}}) rather than one list, so rows cannot be addressed by a fixed path.
- ~~`get_product`~~ not offered: No single-offering endpoint; offerings are only listed per category (GET /offering/list).
- ~~`track`~~ not offered: No tracking-events endpoint; the order carries tracking_code and tracking_url once shipped (see get_order).

## Credentials

- `PLATFORM_MCP_PEECHO_MERCHANT_API_KEY` — Peecho Merchant API key (dashboard > Settings > API), sent as the merchantApiKey query parameter and inside order/quote bodies. Test-environment keys belong to https://test.www.peecho.com/rest/v3/, which this server does not switch to.
- `PLATFORM_MCP_PEECHO_CURRENCY` — Currency for create_order (required by Peecho, e.g. EUR or USD) and quote_shipping prices (EUR when unset).

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve peecho   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve peecho
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve peecho   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/peecho-mcp`. Python and TypeScript serve identical tools.
