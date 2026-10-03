# Dreamship MCP server

Category: **ecommerce_suppliers** · Docs: https://docs.dreamship.com/ · Verified: 2026-09-24

Served by [platform-mcp-hub](https://github.com/tonyyang0504/platform-mcp) from `catalog/ecommerce_suppliers/dreamship.json`; edit the catalog, not this file.

## Tools

- `me` — `GET /shops/` (https://docs.dreamship.com/reference/listshops)
- `list_products` — `GET /items/` (https://docs.dreamship.com/reference/listitems)
- `get_product` — `GET /items/{id}/` (https://docs.dreamship.com/reference/retrieveitem)
- `create_order` — `POST /orders/` (https://docs.dreamship.com/reference/createorder)
- `get_order` — `GET /orders/{id}/` (https://docs.dreamship.com/reference/retrieveorder)
- ~~`quote_shipping`~~ not offered: GET /items/{item_id}/ship-zones/ lists zones ({countries, group, ship_zone_methods[{method, delivery_days_min, delivery_days_max}]}) without prices and takes no country or quantity; costs sit in ship_zones of GET /items/{id}/ (see get_product `raw`), so there is no quote endpoint for the product_id/country/quantity shape.
- ~~`track`~~ not offered: No tracking-events endpoint; fulfillments[].trackings[{carrier, status, tracking_number, tracking_url}] are part of GET /orders/{id}/ (see get_order).

## Credentials

- `PLATFORM_MCP_DREAMSHIP_API_KEY` — Dreamship API key from Settings (https://dreamship.com/app/settings), sent as `Authorization: Bearer <API_KEY>`.
- `PLATFORM_MCP_DREAMSHIP_TEST_ORDER` — Set to true to send `test_order: true` on create_order (test orders are not billed or fulfilled); left out of the body when unset, so orders are real.

## Run

**Unpublished — run from source.** platform-mcp-hub is not on PyPI or npm yet; do not install the name from a registry until it is (anyone could register it first).

    uvx --from git+https://github.com/tonyyang0504/platform-mcp platform-mcp-hub serve dreamship   # Python, stdio
    git clone https://github.com/tonyyang0504/platform-mcp && cd platform-mcp && uv run platform-mcp-hub serve dreamship
    cd runtime/typescript && npm ci --ignore-scripts && npm run build && node dist/cli.js serve dreamship   # TypeScript

Add `--http --port 8000` for Streamable HTTP on 127.0.0.1. Registry name: `io.github.tonyyang0504/dreamship-mcp`. Python and TypeScript serve identical tools.
